# Dev Agent Protocol — AHORA ES UNA SKILL

> ⚠️ Este protocolo dejó de ser una carpeta de docs y es ahora una **skill** portable.
> La fuente de verdad es **[`.claude/skills/dev-protocol/SKILL.md`](./.claude/skills/dev-protocol/SKILL.md)** (symlink a `.agents/skills/dev-protocol/`).

## Cómo cargarlo

- **Auto / explícito**: `Usando dev-protocol, <qué hacer / mejorar / arreglar>` (o `/dev-protocol`). La skill auto-dispara en tareas del stack Python/`uv` + LLM.

## Mapa de secciones (las menciones `dev-protocol §X` del repo apuntan acá)

El `SKILL.md` es un router liviano; los módulos se leen bajo demanda:

- **§1 Rol**, **§2 Estilo cognitivo**, **§3 Entorno y tooling** (`uv` §3.1 / reglas LLM §3.2 / frontend `pnpm` §3.3) → en [`SKILL.md`](./.claude/skills/dev-protocol/SKILL.md).
- **§0 Flujo idea → entrega** (con approval gate) → en [`SKILL.md`](./.claude/skills/dev-protocol/SKILL.md).
- Diseño + TDD → [`code-design.md`](./.claude/skills/dev-protocol/code-design.md).
- Debugging (6 fases) → [`debugging.md`](./.claude/skills/dev-protocol/debugging.md).
- Review de dos ejes + issues → [`qa-review.md`](./.claude/skills/dev-protocol/qa-review.md).
- Git workflow + pre-commit → [`git-workflow.md`](./.claude/skills/dev-protocol/git-workflow.md).
- Doc-sync (manifest/spec/CONTEXT, §4) → [`documentation.md`](./.claude/skills/dev-protocol/documentation.md).

## Cómo usar / instalar (incluye otros IDEs e IAs)

Guía completa en **[`.claude/skills/dev-protocol/USAGE.md`](./.claude/skills/dev-protocol/USAGE.md)**: cómo encajan los archivos, instalación en Claude Code (per-repo o global), y cómo portarlo a herramientas **sin** mecanismo de skills (Cursor, Gemini CLI, OpenCode, Copilot, Windsurf) apuntando su archivo de reglas a `SKILL.md`.

Resumen rápido:
- **Claude Code**: copiá `.agents/skills/dev-protocol/` al repo + symlink a `.claude/skills/` (o a `~/.claude/skills/` para uso global). Auto-dispara por la `description`.
- **Otros IDEs/IAs**: copiá la carpeta (p. ej. a `docs/dev-protocol/`) y apuntá el archivo de reglas de la herramienta (`.cursor/rules/*.mdc`, `GEMINI.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `.windsurfrules`) a `dev-protocol/SKILL.md`. El auto-trigger y la disclosure progresiva son nativos de Claude Code; en el resto se referencia y el agente lee los módulos cuando los necesita.
- Es agnóstico al proyecto (rutas relativas, sin paths absolutos).
