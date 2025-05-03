import os
import git
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
    return jsonify({"path": path, "content": content})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

