import os
import sys


# --- Files that matter for understanding the latest changes (FPI evolution) ---
FOCUS_FILES = [
    # Backend — RTSS/FPI core (sniffer model + update_trace)
    "backend/app/modules/sniffer.py",
    # Backend — Proxy route (stream_wrapper, full message capture)
    "backend/app/api/routes.py",
    "backend/app/main.py",
    # Backend — Provider abstraction (stream_chat wrapped by FPI)
    "backend/app/modules/providers/base.py",
    "backend/app/modules/providers/ollama.py",
    "backend/app/modules/providers/google.py",
    # Backend — Profiles (named config persistence)
    "backend/app/modules/profiles.py",
    # Backend — context (firewall engine, models, state)
    "backend/app/core/firewall.py",
    "backend/app/core/models.py",
    "backend/app/core/state.py",
    "backend/app/core/settings.py",
    # Backend — tests (includes FPI reconstruction tests)
    "backend/perform_tests.py",
    # Frontend — FPI expandable sniffer UI + Firewall Mode Controls
    "frontend/src/components/SnifferTab.tsx",
    "frontend/src/components/ControlPanel.tsx",
    "frontend/src/App.tsx",
    "frontend/src/store.ts",
    "frontend/src/index.css",
    "frontend/src/config.ts",
    # Documentation
    "architecture_spec.md",
    "manifest.json",
    "backend/scripts/augment_corpus.py",
]


def bundle():
    all_mode = "--all" in sys.argv
    output = "context.txt"
    extensions = (".py", ".tsx", ".ts", ".json", ".md", ".sh")
    skip_dirs = {"node_modules", ".venv", ".git", "__pycache__", ".next", "Claude Exports", "Gemini Exports"}

    # 1. Si existe, lo borramos para generar uno nuevo limpio
    if os.path.exists(output):
        os.remove(output)

    # Normalizar focus files a paths absolutos para comparación
    focus_abs = {os.path.normpath(os.path.join(".", f)) for f in FOCUS_FILES} if not all_mode else None

    file_count = 0
    error_count = 0
    total_bytes = 0
    print_count = 0

    mode_label = "ALL FILES" if all_mode else f"FOCUS MODE ({len(FOCUS_FILES)} files)"

    print("Vamo' a empaquetar todo paqueteadito carajo!!!\n")
    print(f"🔧 Semantic GuardRails Packager")
    print(f"   Mode: {mode_label}")
    print(f"   Output: {output}")
    print(f"   Dumpeando extensiones: {', '.join(extensions)}")
    print(f"   Skipeando directorios: {', '.join(skip_dirs)}")
    print(f"   Scanning from: {os.path.abspath('.')}")
    if not all_mode:
        print(f"   💡 Use --all para exportar todo el codigo")
    print()

    with open(output, "w") as out:
        for root, dirs, files in os.walk("."):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                if file.endswith(extensions) and file != output:
                    filepath = os.path.join(root, file)
                    norm_path = os.path.normpath(filepath)

                    # En focus mode, solo incluir archivos de la lista
                    if focus_abs is not None and norm_path not in focus_abs:
                        continue

                    try:
                        with open(filepath, "r") as f:
                            content = f.read()
                        out.write(f"=== {filepath} ===\n")
                        out.write(content)
                        out.write("\n\n")
                        file_count += 1
                        total_bytes += len(content)
                        
                        status = f"✅ {filepath}"
                        if len(status) > 33:
                            status = status[:30] + "..."
                        print(f"{status:<35}", end="\n" if print_count % 3 == 2 else " ")
                        print_count += 1
                    except Exception as e:
                        out.write(f"=== {filepath} ===\n")
                        out.write(f"Error reading {filepath}: {e}")
                        out.write("\n\n")
                        error_count += 1
                        
                        status = f"❌ {filepath}"
                        if len(status) > 33:
                            status = status[:30] + "..."
                        print(f"{status:<35}", end="\n" if print_count % 3 == 2 else " ")
                        print_count += 1

    if print_count % 3 != 0:
        print()

    print()
    print(f"{'=' * 40}")
    if error_count == 0:
        print(f"✅ OK — {file_count} files packed ({total_bytes:,} bytes) → {output}")
    else:
        print(f"⚠️  DONE with errors — {file_count} files packed, {error_count} errors → {output}")
    print(f"{'=' * 40}")

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(bundle())
