import os
import git
import ast
from flask import Flask, request, jsonify

app = Flask(__name__)

REPO_URL = "https://github.com/Warai777/Elysiad_Bot.git"
REPO_PATH = "elysiad_local"

def update_repo():
    if not os.path.exists(REPO_PATH):
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
