import os
import sys


def bundle():
    output = "context.txt"
    extensions = (".py", ".tsx", ".ts", ".json", ".md", ".sh")
    skip_dirs = {"node_modules", ".venv", ".git", "__pycache__", ".next", "Claude Exports", "Gemini Exports"}

    # 1. Si existe, lo borramos para generar uno nuevo limpio
    if os.path.exists(output):
        os.remove(output)

    file_count = 0
    error_count = 0
    total_bytes = 0
    print_count = 0

    print("Vamo' a empaquetar todo paqueteadito carajo!!!\n")
    print(f"🔧 Semantic GuardRails Packager")
    print(f"   Output: {output}")
    print(f"   Dumpeando extensiones: {', '.join(extensions)}")
    print(f"   Skipeando directorios: {', '.join(skip_dirs)}")
    print(f"   Scanning from: {os.path.abspath('.')}")
    print()

    with open(output, "w") as out:
        for root, dirs, files in os.walk("."):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                if file.endswith(extensions) and file != output:
                    filepath = os.path.join(root, file)
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
