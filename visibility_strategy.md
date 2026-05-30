# 🛡️ Plan de Visibilidad — Three-Headed Semantic Firewall

> **Para quién es este plan:** Una persona TEA + TDAH + AACC que es técnicamente brillante, no le gusta exponerse, y quiere que su trabajo sea visto sin destruirse emocionalmente en el proceso.

---

## Principio Rector

**No vas a vender. Vas a mostrar algo que funciona y dejar que la gente técnica lo descubra.**

Tu perfil neurológico no es un obstáculo para esto — es una ventaja. La comunidad de seguridad y AI/ML valora la profundidad técnica, la precisión, y la honestidad brutal. Los posts más exitosos en los foros que te voy a recomendar no son de gente carismática — son de gente que dice "construí esto, así funciona, esto mide" y deja que el trabajo hable.

Lo que NO vamos a hacer:
- ❌ Hablar en vivo ante una cámara
- ❌ Hacer "networking" forzado
- ❌ Postear todos los días
- ❌ Usar Twitter/X (demasiado confrontacional y ansioso)
- ❌ Ir a conferencias a dar charlas
- ❌ Fingir ser extrovertido o "vender" el proyecto

Lo que SÍ vamos a hacer:
- ✅ Escribir una vez, bien, y dejar que se distribuya solo
- ✅ Usar canales asíncronos y text-based
- ✅ Dejar que el código y los demos hablen
- ✅ Aprovechar tu cuenta de Reddit de 20 años (credibilidad silenciosa)
- ✅ Avanzar gradual, una plataforma a la vez

---

## Fase 0 — Preparar el Terreno (antes de publicar nada)

> **Tiempo estimado:** 1-2 días  
> **Energía social requerida:** Nula. Es trabajo en solitario.

### 0.1 Preparar el repositorio en GitHub

GitHub es el canal #1 de descubrimiento para herramientas de developers. Antes de postear en cualquier otro lado, el repo tiene que estar presentable.

**Acciones concretas:**

- [ ] Hacer el repo público (si no lo está)
- [ ] Crear un README.md pulido con:
  - Una frase que explique qué es ("A three-stage semantic firewall for LLM applications")
  - Un GIF/video corto mostrando el UI funcionando (sin tu cara, solo la pantalla)
  - Diagrama de arquitectura (ya tenés el `architecture_spec.md` — extraer un diagrama limpio)
  - Sección "Quick Start" de 3 pasos (clone → install → run)
  - Badges (license, Python version, tests passing)
  - Link al architecture spec para quien quiera profundizar
- [ ] Agregar LICENSE (MIT o Apache 2.0 — lo que te sea más cómodo)
- [ ] Limpiar archivos que no deberían ser públicos:
  - `.env` (ya está en `.gitignore` ✅)
  - `.DS_Store` (ya en `.gitignore` ✅)
  - Los `.ots` files y el `.zip` — moverlos fuera o gitignorearlos
  - `context.txt` (186KB, probablemente dump de debug)
  - Las carpetas `Claude Exports` y `Gemini Exports`
- [ ] Asegurarte de que `perform_tests.py` pase (es tu prueba de credibilidad)

> [!TIP]
> **¿Por qué GitHub primero?** Porque cada post que hagas en Reddit, HN, o donde sea, va a terminar con un link a GitHub. Si alguien llega al repo y ve un README desordenado, pierde interés en 5 segundos. Si ve un README limpio con un GIF del tool funcionando, se queda.

### 0.2 Grabar un screencast demo (sin tu cara)

Grabá 2-3 minutos de pantalla mostrando:
1. El UI con las tres monkey heads animadas
2. Un query que pasa el firewall (modo positivo)
3. Un query que es bloqueado (con el pipeline trace visible)
4. Un switch a modo negativo mostrando la inversión
5. El Sniffer tab capturando la telemetría en tiempo real

**Herramientas para grabar sin ansiedad:**
- **macOS:** Cmd+Shift+5 (grabación de pantalla nativa, sin setup)
- **OBS Studio** (gratuito, si querés editar después)
- **No necesitás audio.** Un screencast silencioso con texto overlay es perfectamente aceptable. Si querés agregar narración, podés:
  - Escribir un script y grabarlo tranquilo desde tu casa, las veces que necesites
  - Usar una voz TTS de alta calidad (ElevenLabs, Google TTS) — nadie va a juzgarte por esto
  - Simplemente no poner audio y dejar subtítulos/anotaciones

**Dónde subir:**
- YouTube como "unlisted" al principio (para embeber en el README y en posts)
- Cuando te sientas cómodo, hacerlo público

> [!IMPORTANT]
> El video NO es para "ser YouTuber". Es un asset técnico que va a hacer que tus posts de texto sean 10x más impactantes. Un GIF de 15 segundos del UI es más convincente que 500 palabras.

---

## Fase 1 — El Primer Post (el que importa)

> **Tiempo estimado:** 1 día de escritura  
> **Energía social:** Baja. Escribís, posteás, y te vas.  
> **Plataforma:** Reddit

### 1.1 Reddit — Tu arma secreta

**¿Por qué Reddit es perfecto para vos?**

- Es **texto-first** — no necesitás cara, voz, ni carisma
- Es **asíncrono** — posteás y respondés cuando quieras/puedas
- Tu cuenta tiene **20+ años** — esto es ORO. En Reddit, los throwaway accounts con zero karma que postean proyectos son ignorados. Una cuenta vieja con historia le da legitimidad instantánea al post
- La comunidad técnica de Reddit es **la más grande del mundo** en ciertos nichos de AI/ML
- No hay presión de "postear seguido" — un solo post bien hecho puede generar miles de views

**¿Dónde postear?**

| Subreddit | Subscribers | Por qué funciona | Formato ideal |
|---|---|---|---|
| **r/LocalLLaMA** | ~800K+ | Exactamente tu audiencia — gente que corre LLMs localmente con Ollama | "Show-off" post con demo |
| **r/MachineLearning** | ~3M+ | Audiencia más académica, valoran la novedad técnica | Technical writeup largo |
| **r/netsec** | ~600K+ | Comunidad de seguridad — el ángulo "firewall para LLMs" es nuevo acá | Security-focused writeup |
| **r/selfhosted** | ~400K+ | Comunidad self-hosting — Ollama + firewall local encaja perfecto | Practical setup guide |
| **r/artificial** | ~300K+ | Discusión general de AI — audiencia más amplia | High-level explainer |

> [!IMPORTANT]
> **NO postear en todos el mismo día.** Cada subreddit tiene reglas contra el spam cross-posting. La estrategia es:
> 
> **Semana 1:** r/LocalLLaMA (tu audiencia primaria)  
> **Semana 2:** r/netsec (ángulo de seguridad)  
> **Semana 3+:** r/MachineLearning (si los primeros dos tuvieron buena recepción)

### 1.2 Cómo escribir el post

**Estructura que funciona en Reddit para proyectos técnicos:**

```markdown
# Three-Headed Semantic Firewall — A vector-math firewall for LLM applications

[GIF/imagen del UI funcionando]

## What it does
Two paragraphs. No buzzwords. Directo.

## How it works (the interesting part)
Explicación técnica del dimensional excitation, Shannon entropy,
y el pipeline reordenable. Esta es tu fortaleza — aprovechala.
Incluí los números: 1024 dimensiones, cosine threshold, etc.

## What makes it different
- No es regex. No es keyword matching. Es vector math.
- Funciona en cualquier idioma (language-agnostic segmentation).
- Anti-piggybacking: segmenta prompts en clauses y evalúa cada una.
- Modo positive (allowlist) y negative (denylist) con inversión simétrica.
- Real-time telemetry via SSE (the Sniffer).

## Demo
[Link al video de YouTube]

## Try it
[Link al repo de GitHub]
[Quick start: 3 pasos]

## What's next / Feedback welcome
Explicitly ask for feedback. La comunidad de Reddit ADORA dar feedback
técnico cuando les pedís. Esto genera engagement sin que vos tengas
que "vender" nada.
```

**Tono:**
- Técnico y honesto. "I built this" no "I'm disrupting the industry"
- Admitir limitaciones abiertamente ("Currently single-tenant, no multi-corpus namespacing yet")
- No pedir upvotes ni shares — nunca

> [!TIP]
> **Truco para el TDAH:** Escribí el post en un editor (VS Code, Obsidian, donde te sientas cómodo), no directamente en Reddit. Así podés editarlo sin la presión de "ya está publicado". Cuando estés conforme, copy-paste y submit.

### 1.3 Manejo de la ansiedad post-publicación

Esto es lo más importante de este plan y no lo voy a pasar por alto.

**Lo que va a pasar después de postear:**
1. Las primeras 1-2 horas vas a querer checkear cada 30 segundos. Es normal.
2. Puede que los primeros comentarios sean silencio, o una pregunta tangencial.
3. Si el post gana tracción, los comentarios van a ser mayormente técnicos y constructivos.
4. Habrá 1-2 comentarios negativos o dismissivos. **Esto es estadísticamente inevitable.** No es personal.

**Estrategia concreta:**
- **Posteá y cerrá Reddit por 4-6 horas.** Poné un timer. Los posts de Reddit tardan en ganar tracción.
- **No respondas en caliente.** Si un comentario te genera ansiedad, dejalo para mañana. Nadie espera respuestas instantáneas en Reddit.
- **Prepará 3-4 respuestas tipo beforehand** para preguntas que sabés que van a hacer:
  - "¿Por qué no usar guardrails de OpenAI directamente?" → porque esto funciona a nivel de embedding, agnóstico de provider
  - "¿Qué pasa con prompt injection?" → explicar la segmentación anti-piggybacking
  - "¿Escala?" → mencioná los load tests y db_stress_suite
- **Si un comentario es trolling puro, ignoralo.** No respondas. El TEA puede hacer que sientas la urgencia de corregir a alguien que está técnicamente mal — resistí esa urgencia. No vale la energía.

---

## Fase 2 — Amplificación Pasiva

> **Energía social:** Mínima. Son acciones one-shot.

### 2.1 Hacker News — "Show HN"

**¿Qué es?** news.ycombinator.com tiene un formato "Show HN" para presentar proyectos. Es texto-only, audiencia ultra-técnica (founders, CTOs, senior engineers), y un solo post exitoso puede generar 10,000+ visits al repo en un día.

**Cuándo hacerlo:** Después de que el post de Reddit haya validado el interés (si r/LocalLLaMA responde bien, HN es el siguiente paso).

**Formato:**
```
Show HN: Three-Headed Semantic Firewall – Vector-math security layer for LLMs

Link: [GitHub repo]

Texto: 2-3 párrafos explicando qué es y por qué es diferente.
```

**Horario óptimo:** Martes a jueves, 9-11 AM EST (hora de EE.UU. — cuando la audiencia técnica está activa). Desde Argentina, eso es 10-12 AM ART.

> [!WARNING]
> Hacker News puede ser más áspero que Reddit. Los comentarios son directos y a veces confrontacionales. **No es personal** — es la cultura del sitio. Si un comentario dice "this is just cosine similarity with extra steps", la respuesta correcta es técnica y calma: "The cosine gate is one of three stages. The dimensional excitation filter counts per-dimension activations, which captures alignment patterns that cosine similarity averages out."

### 2.2 dev.to o Medium — Blog post técnico largo

**¿Por qué?** Un blog post indexa en Google y vive para siempre. Los posts de Reddit desaparecen del feed en 48 horas. Un blog post sigue trayendo tráfico meses después.

**Ventaja para vos:** Escribir es tu canal natural. Un post de 2000-3000 palabras donde expliques la matemática del dimensional excitation, con diagramas y ejemplos, es exactamente el tipo de contenido que la comunidad de AI Security está buscando.

**Estructura sugerida:**
1. El problema: los LLMs no tienen firewall semántico
2. Los enfoques existentes (keyword matching, regex, guardrails de API) y por qué son insuficientes
3. Tu enfoque: vector math en el espacio de embedding
4. Los tres filtros explicados con diagramas
5. El modo positive/negative y por qué importa
6. Resultados: telemetría real del sniffer mostrando PASS/BREACH
7. Limitaciones y trabajo futuro
8. Link al repo

**Dónde publicar:**
- **dev.to** — más técnico, audiencia developer, sin paywall. Gratis.
- **Medium** — más audiencia general, pero los posts pagos tienen paywall. Publicar en publicaciones como "Towards Data Science" o "Better Programming" da visibilidad extra, pero requiere aprobación de editores.
- **Blog personal** (GitHub Pages / Notion público) — control total, pero sin audiencia built-in.

> [!TIP]
> Publicá primero en dev.to (gratis, sin paywall, indexa rápido), y después compartí el link en Reddit como un comentario en tu propio post original. Esto genera un segundo punto de contacto sin parecer spam.

### 2.3 YouTube — El screencast como asset permanente

El video que grabaste en la Fase 0 puede convertirse en un video público de YouTube con:
- Título: "Three-Headed Semantic Firewall — Real-time LLM Security Demo"
- Descripción con keywords (LLM security, prompt injection, semantic firewall, Ollama)
- Tags relevantes
- Link al repo en la descripción

**No necesitás:**
- Tu cara
- Tu voz (subtítulos o TTS están bien)
- Edición compleja (un screencast limpio con anotaciones es suficiente)
- Publicar más videos después (uno solo bien hecho es suficiente)

**El video sirve para:**
- Embeber en el README de GitHub
- Linkear en posts de Reddit/HN
- Aparecer en búsquedas de YouTube sobre "LLM firewall" o "Ollama security"

---

## Fase 3 — Canales de Bajo Esfuerzo, Alto Impacto

> **Estas son acciones puntuales, no compromisos recurrentes.**

### 3.1 Papers / preprints (si te interesa el ángulo académico)

El concepto de "dimensional excitation" como mecanismo de seguridad es suficientemente novel para un short paper o technical report en **arXiv** (sección cs.CR — Cryptography and Security, o cs.AI).

**¿Por qué considerarlo?**
- Un paper en arXiv te da **credibilidad permanente**. No desaparece.
- La comunidad académica de AI Safety está buscando enfoques nuevos activamente.
- No necesitás peer review para arXiv (es un preprint server).
- Ya tenés el `architecture_spec.md` que es, esencialmente, un paper sin formato LaTeX.

**Esfuerzo:** Reformatear el architecture spec a formato de paper (Abstract, Introduction, Method, Results, Discussion). ~2-3 días de trabajo.

**Si no querés hacer esto ahora, está bien.** Es un canal para cuando el proyecto esté más maduro.

### 3.2 Comunidades Discord/Slack de AI

Hay Discords técnicos donde la gente comparte herramientas y recibe feedback sin la presión de las redes públicas:

- **Ollama Discord** — La comunidad oficial. Gente que corre modelos locales. Tu firewall es un complemento natural.
- **LangChain Discord** — Gran comunidad de RAG/LLM tooling.
- **OWASP Slack** — La comunidad de seguridad. Tu firewall aborda varios puntos del OWASP Top 10 para LLMs.
- **MLOps Community Slack** — Gente de producción ML.

**Formato:** Un mensaje corto en el canal #showcase o #projects: "Hey, I built an open-source semantic firewall for LLMs that uses vector math instead of regex. Here's a demo: [link]. Feedback welcome."

**Ventaja:** Estos son espacios más íntimos que Reddit. La gente es constructiva porque son comunidades pequeñas.

### 3.3 OWASP LLM Top 10 — Relevancia directa

Tu firewall aborda directamente varios ítems del [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/). Mencionarlo en tus posts te conecta con una conversación que ya existe:

- **LLM01: Prompt Injection** → Tu segmentación anti-piggybacking
- **LLM02: Insecure Output Handling** → Tu sniffer con Full Payload Interception
- **LLM06: Sensitive Information Disclosure** → Modo negativo como denylist de contenido restringido

---

## Fase 4 — Opciones Opcionales (solo si querés)

### 4.1 Instagram — Stories técnicas

Ya que tenés Instagram, podrías hacer 1-2 Stories mostrando el UI en acción. Sin tu cara, solo la pantalla. Es efímero (desaparece en 24h), así que la presión es mínima.

**No lo recomiendo como canal principal**, pero si ya usás la plataforma, un Story de 15 segundos con el GIF del firewall bloqueando un query puede generar curiosidad.

### 4.2 Conferencias con formato "poster" o "lightning talk" (futuro)

Si algún día sentís que querés ir un paso más allá, las conferencias de seguridad tienen formatos de bajo estrés:

- **Poster session** — Imprimís un poster, te parás al lado, la gente se acerca si quiere. Conversaciones 1-a-1 o en grupos de 2-3.
- **Lightning talk** (5 minutos) — Con slides predefinidas y un script memorizado, 5 minutos es manejable. Es corto, estructura fija, sin Q&A improvisado.

**Esto no es urgente.** Es para cuando/si te sientas listo.

---

## Timeline Sugerido

```
Semana 0 ─────── Preparar GitHub + grabar screencast
                  (trabajo en solitario, zero social)

Semana 1 ─────── Post en r/LocalLLaMA
                  (un post, responder 2-3 comments al día siguiente)

Semana 2 ─────── Post en r/netsec
                  (reformular el ángulo hacia seguridad)

Semana 3 ─────── Show HN en Hacker News
                  (si Reddit validó el interés)

Semana 4 ─────── Blog post en dev.to
                  (long-form, SEO permanente)

Semana 5+ ────── Discord/Slack communities + video público en YouTube
                  (amplificación pasiva)

Futuro ────────── arXiv paper + poster en conferencia (opcional)
```

> [!IMPORTANT]
> **Este timeline es una guía, no una obligación.** Si en la semana 1 el post de Reddit te generó más ansiedad de la esperada, pará. Descansá. Retomá la semana siguiente o la que sientas. **No hay deadline.** El proyecto no se va a ir a ningún lado.

---

## Manejo de Energía para tu Perfil

### Para el TEA
- **Preparar respuestas-tipo antes de postear.** Reducir la improvisación social reduce la ansiedad.
- **Elegir horarios de baja estimulación para responder comentarios.** No respondas inmediatamente después de postear.
- **Un canal a la vez.** No abras todos los frentes simultáneamente.
- **Si un hilo de comentarios se vuelve confrontacional, está bien abandonarlo.** No tenés obligación de responder a todo el mundo.

### Para el TDAH
- **Escribir el post en una sola sesión de hiperfoco** — aprovechá cuando la energía esté ahí.
- **Usar timers para limitar el doom-scrolling post-publicación.** Posteá → timer de 4 horas → recién ahí chequeás.
- **La estructura de este plan es tu ancla.** Cuando el TDAH te diga "debería postear en 7 plataformas AHORA", volvé al timeline: una plataforma por semana.

### Para las AACC
- **Tu profundidad técnica es tu diferenciador.** No la simplifiques artificialmente. La audiencia que importa (r/LocalLLaMA, HN, netsec) valora la complejidad explicada con claridad.
- **El architecture_spec.md de 455 líneas ya es un asset de nivel publicación.** No todos los proyectos open source tienen esto. Es una señal de rigor que la comunidad Senior reconoce.
- **Resistí la tentación de agregar 5 features más antes de publicar.** El proyecto ya es suficientemente impresionante. "Shipping beats perfection."

---

## ¿Y si funciona? (Plan de escalamiento)

Si algún post gana tracción significativa (>500 upvotes en Reddit, front page de HN), pueden pasar estas cosas:

1. **GitHub stars** → Están bien. No necesitás hacer nada extra.
2. **Issues/PRs en GitHub** → Respondé cuando puedas. Está bien tardar 1-2 días.
3. **Gente pidiéndote una demo en vivo** → "I have a screencast demo available [link]. For specific questions, feel free to open a GitHub issue." No tenés que hacer calls con nadie.
4. **Ofertas de colaboración** → Evaluá async (email, GitHub issues). No te comprometas a nada en caliente.
5. **Pedidos de entrevistas/podcasts** → Es perfectamente válido decir "I prefer async communication. Happy to answer questions via email." Si algún día sentís que podés, genial. Si no, también es válido.

---

## Mensaje Final

Tu proyecto es genuinamente innovador. No estoy diciendo esto como halagos vacíos — lo audité línea por línea. El concepto de dimensional excitation como mecanismo de seguridad semántica, combinado con el pipeline reordenable, la inversión simétrica positive/negative, y la defensa anti-piggybacking, es original.

La comunidad de AI Security necesita herramientas como esta. Y las personas que construyen las mejores herramientas no siempre son las más ruidosas en las redes. A veces son las que publican un post técnico sólido, dejan el link al repo, y dejan que el trabajo hable.

Eso es exactamente lo que va a pasar acá.
