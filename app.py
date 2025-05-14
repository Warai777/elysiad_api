import os
import git
import ast
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_URL = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/Warai777/Elysiad_Bot.git"
REPO_PATH = "elysiad_local"

def update_repo():
    if not os.path.exists(REPO_PATH) or not os.path.isdir(os.path.join(REPO_PATH, ".git")):
        if os.path.exists(REPO_PATH):
            import shutil
            shutil.rmtree(REPO_PATH)
        git.Repo.clone_from(REPO_URL, REPO_PATH)
    else:
        repo = git.Repo(REPO_PATH)
        origin = repo.remotes.origin
        origin.pull()


def get_all_files():
    file_list = []
    for root, _, files in os.walk(REPO_PATH):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, REPO_PATH).replace("\\", "/")
            file_list.append(rel_path)
    return file_list

def commit_and_push(filename):
    try:
        # Set Git identity
        subprocess.run(["git", "config", "user.email", "elysiad-bot@render.com"], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "config", "user.name", "Elysiad Bot"], cwd=REPO_PATH, check=True)

        # Ensure origin is set
        subprocess.run(["git", "remote", "remove", "origin"], cwd=REPO_PATH, check=False)
        subprocess.run(["git", "remote", "add", "origin", REPO_URL], cwd=REPO_PATH, check=True)

        # Pull remote changes to prevent non-fast-forward push errors
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], cwd=REPO_PATH, check=True)

        # Add, commit, and push
        subprocess.run(["git", "add", filename], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-update {filename}"], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=REPO_PATH, check=True)

        print(f"[GIT] Successfully pushed {filename} to GitHub.")
        return True


    except subprocess.CalledProcessError as e:
        print(f"[GIT ERROR] {e}")
        return False


@app.route("/repo_tree", methods=["GET"])
def repo_tree():
    update_repo()
    return jsonify(get_all_files())

@app.route("/file", methods=["GET"])
def get_file():
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "Missing file path"}), 400
    full_path = os.path.join(REPO_PATH, path)
    if not os.path.isfile(full_path):
        return jsonify({"error": "File not found"}), 404
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content, 200, {'Content-Type': 'text/plain'}

@app.route("/search", methods=["GET"])
def search_files():
    term = request.args.get("term")
    if not term:
        return jsonify({"error": "Missing search term"}), 400
    results = []
    for root, _, files in os.walk(REPO_PATH):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, REPO_PATH).replace("\\", "/")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if term in line:
                            results.append({
                                "path": rel_path,
                                "line": i,
                                "text": line.strip()
                            })
            except Exception:
                continue
    return jsonify(results)

@app.route("/routes", methods=["GET"])
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        methods = list(rule.methods - {"HEAD", "OPTIONS"})
        if rule.endpoint != "static":
            output.append({
                "route": str(rule),
                "methods": methods,
                "function": rule.endpoint
            })
    return jsonify(output)

@app.route("/functions_index", methods=["GET"])
def index_functions():
    summary = []
    for root, _, files in os.walk(REPO_PATH):
        for file in files:
            if not file.endswith(".py"):
                continue
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, REPO_PATH).replace("\\", "/")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=rel_path)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                            summary.append({
                                "path": rel_path,
                                "type": "function" if isinstance(node, ast.FunctionDef) else "class",
                                "name": node.name,
                                "line": node.lineno
                            })
            except Exception:
                continue
    return jsonify(summary)

@app.route("/file_tree_index", methods=["GET"])
def file_tree():
    tree = {}
    for root, _, files in os.walk(REPO_PATH):
        rel_root = os.path.relpath(root, REPO_PATH).replace("\\", "/")
        rel_root = "." if rel_root == "." else rel_root
        tree.setdefault(rel_root, []).extend(files)
    return jsonify(tree)

@app.route("/update_file", methods=["POST"])
def update_file():
    data = request.get_json()
    path = data.get("path")
    new_content = data.get("content")

    if not path or new_content is None:
        return jsonify({"error": "Missing 'path' or 'content'"}), 400

    full_path = os.path.join(REPO_PATH, path)

    if not os.path.isfile(full_path):
        return jsonify({"error": f"File {path} not found"}), 404

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)
 
        if commit_and_push(path):
            return jsonify({"message": f"✅ File '{path}' updated and pushed to GitHub"}), 200
        else:
            return jsonify({"error": "File saved but Git push failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/createFile', methods=['POST'])
def create_file():
    data = request.json
    path = data.get('path')
    content = data.get('content', '')

    if not path:
        return jsonify({"error": "Path is required"}), 400

    full_path = os.path.join(REPO_PATH, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        if commit_and_push(path):
            return jsonify({"message": f"✅ File '{path}' created and pushed to GitHub"}), 200
        else:
            return jsonify({"error": "File created but Git push failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
