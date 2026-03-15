import os

def bundle():
    output = "context.txt"
    with open(output, "w") as out:
        for root, dirs, files in os.walk("."):
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            if ".venv" in dirs:
                dirs.remove(".venv")
            if ".git" in dirs:
                dirs.remove(".git")
            for file in files:
                if file.endswith((".py", ".tsx", ".ts", ".json", ".md", ".sh")) and file != "context.txt":
                    filepath = os.path.join(root, file)
                    out.write(f"=== {filepath} ===\\n")
                    try:
                        with open(filepath, "r") as f:
                            out.write(f.read())
                    except Exception as e:
                        out.write(f"Error reading {filepath}: {e}")
                    out.write("\\n\\n")

if __name__ == "__main__":
    bundle()
