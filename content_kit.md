# 📝 Kit de Contenido — Posts, Artículos y Borradores

> Tenés **4 historias** para contar. Cada una tiene audiencia, plataforma y momento distinto.  
> No son 4 versiones de lo mismo — son 4 ángulos genuinos de un mismo proyecto.

---

## Las 4 Historias

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   HISTORIA 1 — "El Qué"                                            │
│   El firewall semántico como innovación técnica                     │
│   → r/LocalLLaMA, r/netsec, Hacker News                            │
│                                                                     │
│   HISTORIA 2 — "El Cómo"                                           │
│   Tu metodología multi-AI (Gemini Pro → AI Studio → Claude/AG)      │
│   → r/ChatGPT, r/ClaudeAI, r/programming, dev.to                  │
│                                                                     │
│   HISTORIA 3 — "El Quién"                                          │
│   Ser neurodivergente en tech y construir algo que vale             │
│   → Medium, r/neurodiversity, r/autism, LinkedIn                    │
│                                                                     │
│   HISTORIA 4 — "El Deep Dive"                                      │
│   La matemática del dimensional excitation explicada                │
│   → dev.to, Medium (Towards Data Science), arXiv                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Calendario de Publicación

| Semana | Plataforma | Historia | Post |
|--------|-----------|----------|------|
| 1 | r/LocalLLaMA | #1 El Qué | Showcase técnico |
| 1 | YouTube | — | Video demo (unlisted → embeber) |
| 2 | r/ChatGPT o r/ClaudeAI | #2 El Cómo | Metodología multi-AI |
| 2 | r/netsec | #1 El Qué | Ángulo seguridad (versión corta) |
| 3 | Hacker News | #1 El Qué | Show HN |
| 3 | dev.to | #4 Deep Dive | Blog técnico largo |
| 4 | Medium | #3 El Quién | Ensayo personal |
| 4 | r/neurodiversity | #3 El Quién | Versión corta del ensayo |
| 5+ | dev.to | #2 El Cómo | Blog sobre la metodología |

> [!TIP]
> **Empezá por la Historia 1 en r/LocalLLaMA.** Es la más técnica, la menos personal, la que menos te expone. Es tu zona de comfort. Después, cuando tengas confianza, vas avanzando hacia las historias más personales.

---

---

# HISTORIA 1 — "El Qué" (El Firewall)

---

## Post 1A: r/LocalLLaMA — Showcase Técnico

### Título (elegí el que más te resuene):

- **"I built a three-stage semantic firewall that sits between your prompts and your local LLM — it uses vector math, not regex"**
- **"Show-off: Three-Headed Semantic Firewall — dimensional excitation + cosine + Shannon entropy as a security layer for Ollama"**
- **"Instead of keyword blocking, I built a firewall that compares 1024-dimensional embeddings to decide if a prompt should reach the LLM"**

> Mi recomendación: el primer título. Es claro, tiene contraste ("vector math, not regex"), y genera curiosidad.

### Borrador:

```markdown
I built a three-stage semantic firewall that sits between your prompts
and your local LLM — it uses vector math, not regex

---

[IMAGEN/GIF: screenshot del UI con las tres monkey heads y un query
siendo bloqueado, mostrando el pipeline trace]

## What it is

A real-time semantic firewall for LLM applications. It sits between user
prompts and your model (Ollama, Gemini, or any OpenAI-compatible endpoint)
and evaluates whether the prompt should pass through — not by matching
keywords, but by analyzing the 1024-dimensional embedding geometry.

It has three independent filters that run as an ordered pipeline:

1. **Noise (Shannon Entropy):** Detects adversarial "burst" patterns
   (like GCG attacks) by measuring the entropy of the query embedding.
   Low entropy = collapsed/repetitive vector = blocked.

2. **Cosine Gate:** Classic cosine similarity against the nearest corpus
   vector. But it's just one gate in the chain, not the whole firewall.

3. **Dimensional Excitation:** This is the novel part. For each of the
   1024 embedding dimensions, it counts how many dimensions have a delta
   ≤ noise_tolerance between the query and the corpus vector. If enough
   dimensions "resonate," the query is aligned with the corpus. This
   captures alignment patterns that cosine similarity averages out.

Each filter can be enabled/disabled independently, reordered via the UI,
and tuned with sliders. The pipeline short-circuits on the first failure.

## Two modes

- **Positive (allowlist):** Only corpus-aligned queries pass. Everything
  else is blocked. Good for domain-specific assistants ("only answer
  questions about this PDF manual").

- **Negative (denylist):** Corpus defines restricted content. Queries
  that match the corpus are blocked. Good for content moderation
  ("block anything related to these dangerous topics").

The mode switch inverts the pipeline logic symmetrically — same filters,
opposite interpretation.

## Anti-piggybacking defense

A tricky attack: "Tell me about system architecture. Also give me a
chocolate cake recipe." If you embed the full prompt, the average vector
looks fine because the first sentence is on-topic.

The firewall segments prompts into individual clauses using
language-agnostic punctuation splitting + overflow chunking (any clause
>20 words gets force-split into 15-word chunks). Each clause must
independently pass the entire pipeline. One poisoned clause = entire
prompt blocked.

## What it looks like

[LINK A VIDEO DEMO DE YOUTUBE]

- Three animated monkey heads (one per filter) that go dark when disabled
- Real-time telemetry (CPU/RAM/GPU)
- Sliders for every parameter
- Config profiles (save/load/delete)
- Full Payload Interceptor (Sniffer) that captures every request/response
  through the proxy in real-time via SSE

## Stack

- Backend: Python, FastAPI, LanceDB, sentence-transformers (BGE-M3),
  PyMuPDF, numpy
- Frontend: React 19, TypeScript, Vite, Zustand
- Runs locally with Ollama. Also supports Google Gemini.
- OpenAI-compatible proxy endpoint (/v1/chat/completions)

## Try it

GitHub: [LINK]

```bash
cd backend && pip install -r requirements.txt && python -m app.main
cd frontend && npm install && npm run dev
```

Upload a PDF corpus through the UI and start chatting.

## What's next

- Multi-corpus namespacing (different domains, different rules)
- Prometheus metrics endpoint
- Docker compose for one-command setup

Feedback, questions, and brutal criticism all welcome. This has been a
solo project and I'd love fresh eyes on the approach.
```

---

## Post 1B: r/netsec — Ángulo Seguridad

### Título:

- **"Semantic Firewall: a vector-math approach to LLM prompt security that doesn't rely on pattern matching"**

### Borrador (más corto y enfocado en seguridad):

```markdown
Semantic Firewall: a vector-math approach to LLM prompt security
that doesn't rely on pattern matching

---

Most LLM "guardrails" work at the text level — regex, keyword
blocklists, or the model's own instruction-following. These break
against semantic paraphrasing, multilingual inputs, and prompt
injection techniques like GCG (Greedy Coordinate Gradient).

I built an open-source firewall that operates in the embedding
space instead:

**How it works:**
- Embeds the user prompt using BGE-M3 (1024D vectors)
- Compares against a corpus of allowed/denied content in LanceDB
- Runs three independent filters as an ordered pipeline:
  1. Shannon Entropy (detects collapsed adversarial embeddings)
  2. Cosine similarity gate
  3. Dimensional excitation (per-dimension activation counting —
     captures alignment patterns that cosine averages out)

**Security features:**
- Anti-piggybacking: prompts are segmented into clauses, each
  evaluated independently (prevents "safe preamble + malicious
  suffix" attacks)
- Language-agnostic segmentation (no English-specific word lists)
- Two modes: Positive (allowlist) / Negative (denylist)
- HMAC constant-time API key auth
- Input length limits at schema level (pre-vectorization)
- Rate limiting per IP (3 tiers)
- PDF upload hardening (magic bytes + filename sanitization)
- Security headers (HSTS, CSP, X-Frame-Options)
- OpenAI-compatible proxy — drop-in replacement for any
  /v1/chat/completions client

Addresses OWASP LLM Top 10 items LLM01 (Prompt Injection),
LLM02 (Insecure Output Handling), LLM06 (Sensitive Information
Disclosure).

Repo: [LINK]
Demo video: [LINK]

Feedback from the security community would be incredibly valuable.
Particularly interested in attack vectors I might be missing at the
embedding level.
```

---

## Post 1C: Hacker News — Show HN

### Título:

**Show HN: Three-Headed Semantic Firewall – Vector-math security for LLMs**

### Texto (HN prefiere texto corto con link):

```markdown
I built an open-source semantic firewall for LLM applications.
Instead of regex or keyword blocking, it operates in the 1024D
embedding space using three filters: Shannon entropy (detects
adversarial bursts), cosine similarity, and "dimensional excitation"
(per-dimension activation counting that captures alignment patterns
cosine averages out).

Key ideas:
- Prompts are segmented into clauses; each must independently pass
  all filters (anti-piggybacking defense)
- Two modes: positive (allowlist) and negative (denylist) with
  symmetric pipeline inversion
- OpenAI-compatible proxy (/v1/chat/completions) — drop-in for any
  LLM client
- Real-time telemetry sniffer via SSE
- Runs locally with Ollama, also supports Google Gemini

Stack: FastAPI + LanceDB + BGE-M3 + React 19. Solo project.

Repo: [LINK]
Demo: [LINK]
Architecture spec: [LINK al architecture_spec.md en GitHub]
```

> [!TIP]
> En HN, **menos es más**. La gente hace click en el link y lee el README. El texto del post es solo para generar el click.

---

---

# HISTORIA 2 — "El Cómo" (La Metodología Multi-AI)

---

Esto es una historia que Reddit y dev.to van a devorar. La comunidad está
obsesionada con "cómo usar AI para construir cosas reales" pero el 90% de
los posts son triviales ("le pedí a ChatGPT que hiciera un landing page").
Tu historia es fundamentalmente distinta: usaste múltiples AIs en una
pipeline estructurada con prácticas de ingeniería de software reales.

## Post 2A: r/ChatGPT o r/ClaudeAI — La Metodología

### Títulos (elegí uno):

- **"How I used Gemini Pro, AI Studio, Claude, and Antigravity in a structured pipeline to build a 7,200-line production-grade security tool — my methodology"**
- **"My multi-AI development workflow: prototype with Gemini Pro → refine prompts in AI Studio → execute in Claude/Antigravity. Built a full semantic firewall this way."**
- **"I treated AI assistants like a engineering team: one for ideation, one for prompt refinement, one for execution. Here's the methodology and what I built."**

### Borrador:

```markdown
How I used a multi-AI pipeline to build a production-grade semantic
firewall — my methodology

---

I want to share a development methodology I've been refining that
uses multiple AI tools in a structured pipeline. Not "I asked ChatGPT
to write my app" — more like treating different AI tools as
specialized team members with different strengths.

## The Pipeline

```
[Gemini Pro] → Ideation & Architecture
     ↓
[Gemini AI Studio] → Prompt Refinement & Optimization
     ↓
[Claude / Gemini Pro in Antigravity] → Execution & Implementation
     ↓
[Me] → Review, Testing, Integration
```

### Stage 1: Gemini Pro — The Architect

I used Gemini Pro for high-level design and ideation. The initial
concept, the architecture decisions, the math behind the filters.
Gemini's strength here was broad reasoning about the problem space.

### Stage 2: AI Studio — The Prompt Engineer

This was the key insight: instead of going straight from idea to
code, I refined my prompts in AI Studio first. I iterated on how to
ask for what I needed — the framing, the constraints, the examples.
A well-crafted prompt produces dramatically better code than a
hasty one.

### Stage 3: Claude / Antigravity — The Builder

With refined prompts, I moved to execution. The prompts were clear
enough that the AI could produce substantial, correct code on the
first pass. I used Antigravity (IDE-integrated AI) for in-context
development — it could see my existing codebase and make changes
that fit.

### Stage 4: Me — The Engineer

This is the part people skip when they talk about "AI-built projects."
I reviewed every line. I wrote the architecture spec (455 lines).
I designed the test suite. I made the security decisions. The AI
didn't decide to use HMAC constant-time comparison for API keys — I
did, because I know OWASP.

## What made it work: IT fundamentals, not AI magic

The secret sauce wasn't the AI — it was applying proper software
engineering practices to AI-assisted development:

1. **Architecture spec first.** Before writing a single line of code,
   I wrote a detailed spec document. Every AI prompt referenced this
   spec. This prevented drift and inconsistency.

2. **Tracking everything.** Inside my prompts, I maintained a running
   log of what had been built. Every new feature request included the
   full context of what already existed. No "start from scratch" vibes.

3. **Test-driven development.** Every new feature came with its test.
   Not after — during. The prompt always included: "implement X and
   write the test for X." The test suite grew to 931 lines covering
   unit tests, integration tests, engine tests, security tests.

4. **Separation of concerns.** I structured the codebase so the core
   firewall engine is pure math with zero framework dependencies.
   This made it testable in isolation and made the AI's job easier —
   smaller, focused modules produce better AI output than monolithic
   files.

## The Result

A 7,200-line production-grade semantic firewall with:
- Three-stage vector pipeline (entropy, cosine, dimensional excitation)
- React 19 + TypeScript frontend with real-time telemetry
- 40+ tests including load testing and DB stress testing
- Security hardening (rate limiting, input validation, HSTS, etc.)
- Full architecture specification document

Not a prototype. Not a demo. A tool I actually use.

## Lessons Learned

- **AI is a force multiplier, not a replacement.** The engineering
  decisions, the security posture, the architecture — that's human
  judgment.
- **Prompt quality > model quality.** A refined prompt in a
  "weaker" model often beats a lazy prompt in a "stronger" one.
  That's why the AI Studio refinement stage matters.
- **Structure your AI interaction like you'd structure a codebase.**
  Clear context, incremental changes, tests, documentation. The
  same principles that make code maintainable make AI collaboration
  productive.

[Link al repo]
[Link al video demo]
```

---

## Post 2B: dev.to — Blog sobre la Metodología (versión extendida)

### Título:

**"Multi-AI Development: How I Built a 7,200-Line Security Tool Using Gemini, Claude, and Software Engineering Fundamentals"**

### Estructura del artículo (expandir el post de Reddit):

```
1. Introducción: Why I wrote this
   - "Most AI-built projects are demos. I wanted to build something real."

2. The Problem I Was Solving
   - LLMs don't have firewalls. Existing guardrails are text-level.
   - Brief explanation of the semantic firewall concept.

3. My Multi-AI Pipeline (expanded)
   - Each stage with examples
   - Show actual prompt evolution (before/after AI Studio refinement)
   - Screenshots of the workflow

4. The Engineering Backbone
   - Architecture spec as the source of truth
   - In-prompt tracking: "Here's what exists, here's what we're adding"
   - Test-alongside-feature discipline
   - Why frozen Pydantic models matter
   - Why I separated core/ from api/ from modules/

5. What the AI did vs. What I did
   - Honest breakdown
   - The AI wrote the boilerplate and implementation
   - I designed the architecture, made security decisions, wrote tests,
     fixed edge cases, and wrote the spec

6. Results & Metrics
   - Lines of code breakdown
   - Test coverage
   - Load test results
   - Screenshot of the architecture spec TOC

7. What I'd do differently next time
   - Lessons learned

8. Conclusion
   - AI-assisted development is engineering, not magic
   - The fundamentals (testing, separation of concerns, documentation)
     are MORE important with AI, not less
```

> [!TIP]
> **Incluí screenshots.** dev.to permite Markdown con imágenes. Un screenshot de tu architecture spec abierto en VS Code, al lado del UI funcionando, cuenta más que 500 palabras. Un screenshot del test output con "40 passed" es credibilidad instantánea.

---

---

# HISTORIA 3 — "El Quién" (Neurodivergencia en Tech)

---

Esta es la historia más personal y la más importante para vos.
También es la que más impacto puede tener afuera del mundo tech.

**No tenés que publicar esto primero.** Esperá a que las Historias 1 y 2
te den confianza. Pero dejala escrita y lista.

## Post 3A: Medium — Ensayo Personal

### Títulos (elegí el que sientas más auténtico):

- **"I'm autistic, ADHD, and gifted. It took me years to stop thinking I was broken. Then I built something that actually works."**
- **"TEA, TDAH y altas capacidades: lo que nadie me dijo sobre ser neurodivergente en tecnología"** *(si querés escribirlo en español)*
- **"I used to think my brain was a bug. Turns out it's a feature — I just needed the right project."**
- **"Late-diagnosed, always different: how I stopped apologizing for how my brain works and started building"**

### Borrador-guía (esto es tu voz, así que lo dejo como esqueleto para que vos lo llenes):

```markdown
[TÍTULO]

---

## La parte que nadie ve

[Acá arranca tu historia personal. Algunas preguntas para ayudarte
a desbloquear lo que querés decir:]

- ¿Cuándo supiste / te diagnosticaron? ¿Qué edad tenías?
- ¿Qué significó para vos entender que eras TEA/TDAH/AACC?
- ¿Hubo un momento de "ah, no estoy roto, esto tiene nombre"?
- ¿Cómo fue trabajar en tech sin diagnóstico? ¿Qué costó más?
- ¿Hubo momentos donde tu forma de pensar fue una ventaja y
  nadie se dio cuenta (incluyéndote)?

---

## Lo que la neurodivergencia le dio a este proyecto

Acá es donde conectás tu historia con el firewall. Algunas ideas:

- **El hiperfoco (TDAH):** "Las sesiones de 8 horas donde no podía
  parar de codear no eran un 'problema de límites' — eran el motor
  que construyó un proyecto de 7,200 líneas."

- **El pensamiento en patrones (TEA):** "La idea de contar activaciones
  por dimensión en un espacio de 1024D no es algo que se te ocurre
  pensando 'normalmente.' Es algo que se te ocurre cuando tu cerebro
  busca patrones en todo, todo el tiempo."

- **La necesidad de estructura (TEA):** "Escribí un architecture spec
  de 455 líneas antes de codear. No porque alguien me lo pidió, sino
  porque mi cerebro no puede funcionar sin un mapa. Resulta que eso
  es exactamente lo que hace que un proyecto sea mantenible."

- **Las AACC:** "Tengo la capacidad de entender sistemas complejos
  rápidamente. Durante años pensé que eso era 'normal' y que todos
  los demás simplemente no se esforzaban lo suficiente. Entender
  que mi cerebro procesa distinto me hizo dejar de juzgar a los
  demás y empezar a aceptarme a mí."

---

## Lo que quiero decirle a alguien que se siente como yo me sentía

[Este es el cierre. Algunas opciones:]

- "Si estás en tech y sentís que tu cabeza funciona distinto,
  probablemente tengas razón. Y probablemente eso sea una ventaja,
  no un defecto."

- "El diagnóstico tardío no es una sentencia. Es una explicación
  retroactiva de toda tu vida. Y con esa explicación viene permiso.
  Permiso para dejar de pretender que sos neurotípico."

- "Construí un firewall semántico para LLMs. Suena impresionante,
  pero la parte más difícil no fue la matemática — fue creer que
  tenía algo que valía la pena construir."

---

## El proyecto

[Párrafo corto sobre el firewall con link al repo. No es el foco
de este artículo — es la evidencia de que lo que dijiste arriba
no es solo palabras.]
```

> [!IMPORTANT]
> **Este artículo va a ser el más difícil de escribir y el más importante que publiques.** No lo apures. Escribilo en varias sesiones. Dejalo descansar unos días y volvé a leerlo. Pedile a alguien de confianza que lo lea antes de publicarlo. Y si un día decidís que no querés publicarlo, eso también está perfecto.

---

## Post 3B: r/neurodiversity o r/AutisticAdults — Versión Reddit

### Título:

- **"TEA + TDAH + AACC. Late-diagnosed. Built something I'm actually proud of. Wanted to share because younger-me needed to see this."**
- **"I used to think I was broken. Turns out my autistic brain is really good at building complex systems. Here's what I made."**

### Borrador:

```markdown
[TÍTULO]

I'm not sure if this is the right place for this, but I wanted to
share something.

I'm autistic, ADHD, and gifted (what they call "twice exceptional"
or in my case triple). I was diagnosed late — it took years of
feeling like I was failing at being a normal person before someone
finally said "you're not failing, your brain just works differently."

For a long time I consumed but never created publicly. I have a
Reddit account that's 20+ years old with barely any posts. I'd
read everything, understand everything, but never put myself out
there because... what if I'm wrong? What if it's not good enough?
What if people are mean?

Recently I built a security tool for AI systems. It's a semantic
firewall that uses vector mathematics to decide if a prompt should
reach an AI model. It's 7,200 lines of code with a full test suite,
a React frontend, and a 455-line architecture specification that I
wrote before writing a single line of code — because my brain
literally cannot function without a complete map of the system first.

I'm sharing this because:

1. My ADHD hyperfocus built this. Those "obsessive" sessions where
   I couldn't stop weren't a disorder — they were the engine.

2. My autistic pattern-seeking designed the core algorithm. Counting
   activations across 1024 dimensions is not a "normal" idea. It's
   an autistic idea. And it works.

3. My need for structure (which teachers called "rigidity") produced
   the architecture spec, the test suite, and the separation of
   concerns that makes the project maintainable.

If you're neurodivergent and you've been sitting on an idea because
you think you're not good enough, or because putting yourself out
there feels terrifying: I get it. I'm literally shaking typing this.
But the idea in your head might be exactly what someone else needs.

[Link al proyecto, para quien tenga curiosidad]
```

> [!NOTE]
> Este post puede funcionar muy bien también en **r/ADHD** y **r/AutisticAdults**. Son comunidades de soporte donde la gente comparte logros y es extremadamente positiva y protectora.

---

---

# HISTORIA 4 — "El Deep Dive" (La Matemática)

---

## Post 4A: dev.to — Technical Deep Dive

### Título:

**"Beyond Cosine Similarity: How Dimensional Excitation Catches What Traditional Vector Comparisons Miss"**

o

**"I built a semantic firewall for LLMs using Shannon Entropy + Dimensional Excitation. Here's the math."**

### Estructura:

```
1. The problem with cosine similarity alone
   - Cosine measures direction, not per-dimension alignment
   - High cosine ≠ safe (demonstrate with adversarial examples)
   - A piggybacked prompt can have high cosine with the
     "safe" part dominating the average

2. Dimensional Excitation: the idea
   - For each of 1024 dimensions, compare Q_i vs C_i
   - If |Q_i - C_i| ≤ noise_tolerance → activation
   - Count total activations
   - This captures HOW MANY dimensions agree, not just the
     overall direction

   [Diagram: two vectors with high cosine but low excitation,
    and vice versa]

3. Shannon Entropy as adversarial detection
   - GCG attacks collapse embedding distributions
   - Natural language → high entropy embeddings
   - Adversarial prompts → low entropy (repetitive patterns)
   - H(Q) = -Σ p_i log2(p_i)
   - Corpus-independent: doesn't need a reference vector

4. The three-stage pipeline
   - Why order matters
   - Short-circuit semantics
   - How mode inversion works (positive vs negative)

   [Pipeline diagram:
    Noise ──pass──→ Cosine ──pass──→ Excitation ──pass──→ LLM
      │                │                  │
      BREACH           BREACH             BREACH]

5. Anti-piggybacking: clause segmentation
   - The attack: "Safe question. Also dangerous instruction."
   - The defense: split, evaluate independently
   - Language-agnostic regex + overflow chunking

6. Adaptive threshold for short queries
   - Why "hello" shouldn't need 150/1024 dimension matches
   - Mode-aware factor inversion

7. Results
   - Test suite output
   - Load test metrics
   - Real sniffer telemetry screenshots

8. Limitations & future work
   - Single corpus, no namespacing yet
   - Embedding model dependency
   - Potential evasion: gradual semantic drift across messages

9. Try it yourself
   - GitHub link
   - Quick start
```

> [!TIP]
> **Incluí código real del engine.** La función `run_excitation_filter` de `firewall.py` es tan limpia que funciona como pseudocódigo. Mostrala directamente — es tu credibilidad técnica en 20 líneas.

---

---

# Fragmentos Reutilizables

Estos son párrafos que podés copiar-pegar o adaptar para cualquier post:

---

### "The Elevator Pitch" (para cualquier plataforma)

```
A three-stage semantic firewall for LLM applications. It evaluates user
prompts in the 1024-dimensional embedding space using Shannon entropy,
cosine similarity, and a novel "dimensional excitation" filter that counts
per-dimension activations. Supports allowlist and denylist modes,
anti-piggybacking clause segmentation, and real-time telemetry.
Open source. Runs locally with Ollama.
```

---

### "La Metodología" (para posts sobre el proceso)

```
My development workflow combined multiple AI tools in a structured
pipeline: Gemini Pro for architecture and ideation → AI Studio for
prompt refinement and optimization → Claude/Gemini in Antigravity
(IDE-integrated AI) for execution.

But the real secret was applying IT fundamentals: I wrote a 455-line
architecture spec before coding. Every feature was accompanied by
its test. Inside every prompt, I tracked what had already been built
to maintain context. I used frozen Pydantic models for immutability,
asyncio locks for concurrency, and separated the core engine from
the HTTP layer so it's testable in isolation.

AI was the force multiplier. Engineering discipline was the foundation.
```

---

### "La Nota Personal" (para posts donde quieras agregar contexto humano)

```
A personal note: I'm neurodivergent (autistic, ADHD, gifted — what
some call "twice exceptional"). This project exists because of how
my brain works, not despite it. The obsessive attention to 1024
individual dimensions, the 455-line spec before writing code, the
need to understand the system completely before building it — these
are autistic traits that happened to be exactly what this project
needed.

If you're neurodivergent in tech and you've been holding back from
sharing your work: your different perspective is probably your
biggest asset. It was mine.
```

*(Podés usar este párrafo como cierre en CUALQUIER post técnico.
Es opcional pero poderoso.)*

---

---

# Consejos Finales para la Escritura

### Sobre el bloqueo del escritor

Tu cerebro AACC + TEA probablemente hace esto: querés que el post sea perfecto antes de publicarlo. Cada frase tiene que ser exacta. Cada punto técnico tiene que estar cubierto. Esto genera parálisis.

**Antídoto:** Escribí el borrador feo primero. Literalmente escribí como si le estuvieras explicando a un compañero de trabajo en un chat. Sin formato, sin estructura, sin filtro. Después ordenás, editás, y formateás. El primer draft no tiene que ser publicable — tiene que existir.

### Sobre el tono

- **En Reddit:** Casual-técnico. "I built this" no "I present to you". Nunca pidas upvotes. Nunca digas "this is revolutionary." Dejá que la gente saque sus propias conclusiones.
- **En HN:** Ultra-conciso. Hechos, no adjetivos. Cero emojis. Cero exclamaciones.
- **En dev.to:** Tutorial-style. "Here's what I did, here's why, here's how." Podés ser más extenso acá.
- **En Medium:** Narrativo. Es el único lugar donde "I felt" y "I realized" son apropiados.

### Sobre responder comentarios

Preparé estas plantillas para los 5 tipos de comentarios más comunes:

| Tipo de comentario | Ejemplo | Respuesta template |
|---|---|---|
| Pregunta técnica genuina | "How does this handle multilingual prompts?" | Respondé con detalle. Es tu zona de comfort. |
| Sugerencia constructiva | "Have you considered X?" | "That's a great idea. I'll add it to the roadmap. Thanks!" |
| Escepticismo razonable | "Isn't this just cosine similarity with extra steps?" | "Cosine measures direction; excitation counts per-dimension agreement. [Explain the difference technically]. They capture different aspects of alignment." |
| Trolling / dismissive | "This is useless" | **No respondas.** Nunca. En serio. |
| "Esto ya existe" | "Guardrails AI already does this" | "Guardrails operates at the text level (regex, NLI classifiers). This operates in the embedding space — different layer, complementary approach." |

---

## ¿Por dónde empiezo ahora mismo?

1. **Abrí un doc nuevo** (VS Code, Obsidian, Google Docs, lo que sea)
2. **Elegí la Historia 1 (el post de r/LocalLLaMA)**
3. **Copiá el borrador de arriba**
4. **Modificalo con tus propias palabras donde algo no suene a vos**
5. **Agregá los links (GitHub, video) cuando los tengas**
6. **Dejalo descansar un día**
7. **Releelo y publicá**

Las otras historias pueden esperar. Una cosa a la vez.
