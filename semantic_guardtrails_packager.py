import os
import sys


def bundle():
    output = "context.txt"
    extensions = (".py", ".tsx", ".ts", ".json", ".md", ".sh")
    skip_dirs = {"node_modules", ".venv", ".git", "__pycache__", ".next"}

    file_count = 0
    error_count = 0
    total_bytes = 0

    print(f"🔧 Semantic GuardRails Packager")
    print(f"   Output: {output}")
    print(f"   Extensions: {', '.join(extensions)}")
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
                        print(f"  ✅ {filepath}")
                    except Exception as e:
                        out.write(f"=== {filepath} ===\n")
                        out.write(f"Error reading {filepath}: {e}")
                        out.write("\n\n")
                        error_count += 1
                        print(f"  ❌ {filepath} — {e}", file=sys.stderr)

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
