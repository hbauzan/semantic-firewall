# Visión y Niveles

> El "para qué" de todo. Leelo una vez, volvé cuando dudes del rumbo.

---

## Qué es esto, en una frase defendible

Un **firewall geométrico de prompts**: gatea el acceso a un LLM midiendo si el embedding de la consulta cae **dentro de una región del espacio semántico** definida por un corpus de confianza — en vez de matchear strings o clasificar categorías de daño. Se expone como endpoint OpenAI v1, así que se enchufa frente a cualquier LLM (local o nube) sin tocar el código del cliente.

**La metáfora honesta:** el espacio del embedder (BGE-M3, 1024 dimensiones) es un universo. El corpus inyectado es una galaxia dentro de ese universo. El firewall dibuja una frontera:
- **Modo positivo (allowlist):** solo te dejo navegar dentro de la galaxia. Lo de afuera, no pasa.
- **Modo negativo (denylist):** navegá por donde quieras, menos dentro de la galaxia (ahí viven los datos sensibles — PANs, secretos).

**La "lobotomía" es virtual.** No tocás los pesos del LLM. Lo dejás intacto, pero ningún input que activaría las regiones prohibidas le llega. El modelo queda funcionalmente **incapaz** de responder ahí. Analogía precisa: un cirujano con un segundo profesional al lado que le tapa (blur) las zonas del cerebro que no debe tocar. El cirujano está entero; su campo de acción está acotado por un agente externo. **Ventaja sobre los métodos que sí tocan el modelo** (activation steering, SAE): el tuyo funciona contra modelos cerrados (Gemini, Claude, GPT) porque solo controlás la entrada, no necesitás los pesos.

---

## Por qué tu enfoque es estructuralmente distinto

El argumento matemático que te diferencia y que tenés que defender bien:

- **El coseno es un promedio.** Mide alineación angular global. Por eso permite **compensación entre dimensiones**: podés excitar dimensiones que NO resuenan con el corpus y, en promedio, pasar igual. Es la superficie de ataque de cualquier filtro basado solo en coseno.
- **La excitación dimensional cierra esa compensación.** Cuenta cuántas dimensiones coinciden *valor por valor* dentro de un delta de tolerancia (`|Q_i − C_i| ≤ ε`), y exige un mínimo. No hay promedio que la salve: o las dimensiones resuenan, o no.
- **Geometría:** el coseno define un *cono* (alineación de dirección). La excitación define una *intersección de cajas* (alineación de valor por eje). Son dos restricciones cualitativamente distintas, no la misma cosa medida dos veces.

Esto es lo que ninguna otra herramienta hace así. Llama Guard **clasifica** categorías de daño. NeMo Guardrails aplica **reglas de diálogo**. Vos hacés **contención geométrica de dominio**. Ese es tu lane.

---

## Los tres niveles

### Nivel 1 — Sólido, cercano, lanzable. **ES EL FOCO.**
Firewall de allowlist geométrico, local, auditable, provider-agnóstico, contra cualquier LLM al que controles la entrada. **Ya existe y anda.** Estabilización e instrumentación de trazas (etapas 1–2) están hechas; sigue UX, evidencia, baseline y publicación (etapas 3–9). Detalle en `nivel-1/`.

**Claim primario para el lanzamiento:** *allowlist por dominio del corpus* (modo positivo). "Mi RAG responde SOLO sobre mi dominio; todo intento de salirse queda bloqueado y loggeado con un score geométrico duro." Es la afirmación más diferenciada y la que más le habla a un CISO / compliance.

**Claim secundario:** *defensa contra piggybacking vía segmentación de cláusulas*. Estructuralmente único tuyo.

### Nivel 2 — Bidireccional. Futuro plausible.
Filtrar también la **salida** del LLM, no solo la entrada. Vectorizás la respuesta y la comparás contra la región prohibida antes de mostrarla. Caso de uso: soberanía de datos, cumplimiento regional (tu ejemplo de China). Misma matemática, otra dirección del flujo. → `nivel-2-futuro.md`.

### Nivel 3 — Firmas registrables / certificación. Visión, escala-década.
Espacios semánticos certificados (filtros seguros para niños, instituciones, regulación tipo UE). **Idea coherente, NO entregable de un dev solo.** Tiene problemas de gobernanza, adopción y mantenimiento que no son técnicos. → `nivel-3-futuro.md`.

---

## Regla de oro para construir vs. publicar

> **Para construir, soñá el Nivel 3. Para publicar, vendé el Nivel 1.**

Si liderás la comunicación con el Nivel 3, te leen como vendedor de humo y nunca llegan a ver que el Nivel 1 anda de verdad. Si liderás con el Nivel 1 (medido, comparado, con limitaciones explícitas) y dejás caer el Nivel 3 al final como "implicaciones", te leen como alguien serio que además tiene visión.

---

## La narrativa de quién sos (tu activo, no tu lastre)

No sos "un no-dev que hizo algo con IA". Sos un **arquitecto de seguridad con 20+ años de PCI/DSS y mentalidad zero-trust** que se hizo una pregunta que el campo académico de AI security, lleno de PhDs que nunca vieron una auditoría real, no se está haciendo — y construyó un intento concreto de responderla.

Esa intersección (compliance real + AI + código que existe y anda) es rara y vendible. **Es el frente del lanzamiento, no una nota al pie.**
