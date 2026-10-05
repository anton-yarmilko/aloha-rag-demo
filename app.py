"""Flask front-end for the demo RAG support assistant."""
from flask import Flask, jsonify, render_template, request

from rag import load_sections, search

app = Flask(__name__)
SECTIONS = load_sections()

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/ask")
def ask():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "empty query"}), 400
    hits = search(query, SECTIONS)
    if not hits:
        return jsonify({"answer": "No matching knowledge base entries.", "sources": []})
    best = hits[0]
    return jsonify({
        "answer": best["body"].strip(),
        "matched_section": best["title"],
        "sources": [
            {"section": h["title"], "file": h["source"], "score": h["score"]}
            for h in hits
        ],
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5081, debug=False, use_reloader=False)
