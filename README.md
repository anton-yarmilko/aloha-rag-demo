# aloha-rag-demo

Flask + RAG demo of an AI-assisted support knowledge base, modeled on the internal
platform I built and operate at work (used by ~30 support employees daily).
This public version uses **synthetic NCR Aloha-style data only** - no proprietary content.

## How it works

1. `rag.py` loads every markdown file in `knowledge_base/` and splits it into sections.
2. A query is ranked against sections with a simple TF-IDF-style score (pure Python, no deps).
3. `app.py` (Flask) exposes `/ask?q=...` returning the best-matching answer plus ranked sources.

In the production system this retrieval layer feeds an LLM (ChatGPT) with a
feedback-driven learning loop; the demo returns the retrieved section directly
so it runs fully offline.

## Run it

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000  or:
# curl "http://127.0.0.1:5000/ask?q=kitchen+printer+offline"
```

## Author

Anton Yarmilko - [LinkedIn](https://www.linkedin.com/in/anton-yarmilko-15a220331)
