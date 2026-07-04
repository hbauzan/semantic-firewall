# Etapa 2 — Logging y trazas confiables

> **Estado: HECHA.**

> Objetivo: que las trazas del firewall sean completas, confiables y **exportables a un formato estándar** que después se pueda enchufar a Graylog, Datadog u otro SIEM. La auditabilidad es tu argumento de venta — tiene que ser real, no decorativa.

---

## Por qué esta etapa importa tanto en TU caso

Tu diferencial frente a los métodos que tocan el modelo es: **cada decisión del firewall es un evento auditable con métricas duras.** Un auditor PCI/DSS no te pregunta *cómo* evitaste la fuga — te pregunta que le muestres la traza de cada intento. Si tus logs son sólidos, eso ES el producto. Si son flojos, perdés el argumento más fuerte que tenés.

Ya tenés mucha base (el spec §10 RTSS, §11.7 persistencia, §12 logging rotativo). Esta etapa es **endurecer y estandarizar**, no inventar de cero.

---

## Qué ya existe (según spec, verificar contra código en Etapa 1)
- RTSS (Real-Time Semantic Sniffer): captura cada decisión PASS/BREACH con pipeline trace.
- Full Payload Interception (FPI): captura input completo + respuesta reconstruida.
- Persistencia a `sniffer_history.json` (buffer circular, 1000 entradas).
- `TimedRotatingFileHandler`: rotación diaria, retención 30 días.
- `GET /system/logs/export`: exporta traza + chat history a JSON forense.

---

## Tareas

### Bloque A — Auditar lo que ya logueás
- [x] Generar tráfico de prueba (varios PASS y BREACH, distintos modos, distintos filtros).
- [x] Revisar `firewall.log` y `sniffer_history.json`: ¿está TODO lo que un auditor querría? ¿timestamp, decisión, modo, qué filtro disparó, valor vs. threshold, el prompt segmentado, qué cláusula falló?
- [x] Confirmar que **no se loguean secrets** (API keys, contenido sensible en claro si no corresponde).
- [x] Confirmar la afirmación del spec: emit_trace() se llama en TODOS los caminos terminales (PASS/BREACH) tanto en `/chat` como en `/v1/chat/completions`. Verificar paridad real.

### Bloque B — Formato estándar de salida
- [x] Decidir el formato de export. Recomendado: **JSON estructurado por línea (NDJSON / JSON Lines)** con campos planos. Es lo que Graylog (GELF), Datadog, Splunk y casi todo SIEM ingieren sin fricción.
- [x] Definir un **esquema de evento estable y documentado** (un campo = un significado, nombres consistentes). Ej: `timestamp`, `event_type`, `decision`, `mode`, `filter`, `metric_value`, `threshold`, `clause`, `trace_id`. Versionarlo (`schema_version`).
- [x] Asegurar que `GET /system/logs/export` produzca exactamente ese formato.
- [x] (Opcional, no ahora) un appender que escriba directo en formato GELF si querés demo de Graylog. Documentalo como "soportado vía export + forwarder estándar" — no conéctes el conector todavía.

### Bloque C — Confiabilidad de la traza
- [x] Verificar el contrato de thread-safety del buffer (spec §10.3): si todo corre en el event loop, ok; si hay `asyncio.to_thread` para persistir, confirmar que el snapshot evita races (spec §11.7 dice que sí — verificarlo bajo carga concurrente con el load test).
- [x] Probar resiliencia: corromper `sniffer_history.json` a mano y confirmar que el consumer arranca con `[]` y no crashea (spec lo promete — verificar).
- [x] Confirmar que las excepciones del LLM upstream se reflejan como `status=ERROR` en la traza y no como "falsos OK".

---

## Definición de "Etapa 2 terminada"
- [x] Toda decisión terminal queda logueada con métricas completas, en ambos endpoints.
- [x] Existe un esquema de evento documentado y versionado.
- [x] `GET /system/logs/export` produce ese formato estándar (NDJSON/JSON).
- [x] Probaste que un SIEM estándar podría ingerirlo (aunque sea conceptualmente / con un import manual a una instancia local de Graylog si querés ir más lejos).
- [x] La traza es resiliente a corrupción y refleja errores upstream honestamente.

---

## Trampas
- **No construyas conectores propietarios todavía.** "Exportá NDJSON estándar → un forwarder lo lleva a cualquier SIEM" es suficiente para el lanzamiento y mucho menos trabajo que integrar Datadog/Graylog nativo. Documentá la ruta, no la implementes entera.
- **No loguees de más.** Un log que incluye el contenido sensible en claro es un agujero, no una feature. Pensá qué necesita el auditor vs. qué es PII.

---

## Presupuesto de energía
- Bloque A: 1 micro-sesión.
- Bloque B: 1–2 micro-sesiones (definir esquema es la parte de cabeza).
- Bloque C: 1 micro-sesión.

---

## Prompts sugeridos

**Auditar logging actual:**
```
Leé roadmap/nivel-1/etapa-2-logging.md, Bloque A. Generá tráfico de prueba
(PASS y BREACH en modo positivo y negativo) y mostrame qué queda registrado
en firewall.log y sniffer_history.json. Decime si falta algún campo que un
auditor de seguridad necesitaría y si se está logueando algo sensible que no
debería.
```

**Definir esquema de export estándar:**
```
Leé roadmap/nivel-1/etapa-2-logging.md, Bloque B. Proponeme un esquema de
evento JSON estructurado, plano y versionado, compatible con ingestión a
Graylog/Datadog/Splunk vía forwarder estándar. Después ajustá
GET /system/logs/export para que produzca exactamente ese formato. Mostrame
el esquema antes de implementar.
```
