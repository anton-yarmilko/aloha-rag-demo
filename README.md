# aloha-rag-demo

Flask + retrieval demo of an AI-assisted support knowledge base, modeled on the internal
platform I built and operate at work (used by ~30 support employees daily).
This public version uses **synthetic NCR Aloha-style data only** - no proprietary content.

## How it works

1. `rag.py` loads `##` sections from Markdown files in `knowledge_base/`. Document introductions are excluded from answers; their synthetic-data notice remains in the source and on the homepage.
2. A query is ranked against sections with a simple TF-IDF-style score (pure Python, no retrieval dependencies). Title terms are weighted three times, with word boundaries preserved.
3. `app.py` (Flask) exposes `/ask?q=...` returning the best-matching answer plus ranked sources.

In the production system this retrieval layer feeds an LLM (ChatGPT) with a
feedback-driven learning loop; the demo returns the retrieved section directly
so it runs fully offline after dependencies are installed. **This public repository has no LLM, embeddings, feedback storage or self-learning.** The internal-system description above is author-provided context, not a feature implemented here.

## Retrieval limits

- The included knowledge base is English and synthetic. It is not official NCR guidance, production troubleshooting advice or medical content.
- Tokenization preserves Unicode words and is case-insensitive; it does not translate queries, infer synonyms or understand negation. Ukrainian queries require matching Ukrainian content, which the bundled KB does not contain.
- A small explicit English stop-word list excludes common words such as `the`. A candidate must contain at least half of the unique remaining query tokens. This is a **demo relevance heuristic**, tested on synthetic examples, not a calibrated confidence measure or a guarantee of correctness. Incidental overlaps can still pass; paraphrases can be missed.
- `score` is a lexical ranking value, **not** a probability. No evidence is invented: the answer is a retrieved section verbatim, but synthetic source text itself is not authoritative.
- The index loads at startup; restart after changing Markdown. This small demo does not claim scalable indexing or production readiness.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py  # loopback-only local preview; debugger and reloader disabled
# open http://127.0.0.1:5081  or:
# curl "http://127.0.0.1:5081/ask?q=kitchen+printer+offline"
```

The responsive homepage displays the retrieved text verbatim and ranked source metadata without leaving the page. It handles loading, no match, whitespace-only input, network/HTTP/JSON errors and a 15-second request timeout. JavaScript disabled: the form opens the JSON API instead. No chat history, browser storage, account, analytics, translation or external AI service is added.

The server above is still Flask's **development server**, even with debug off. Do not expose it publicly. Dependencies must be installed or updated in the activated environment; changing a requirement does not update an existing virtualenv automatically.

## Production WSGI preparation (not deployed)

For a later Linux deployment, the application is importable as `app:app`. [Flask's official Gunicorn guide](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/) documents installation and this entrypoint. After installing a reviewed Gunicorn version in a separate environment, a loopback-only smoke-test command is:

```bash
gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
```

Gunicorn is not installed, pinned or tested by this change. This is preparation, not a production-ready deployment. A public release additionally needs an approved server version and dependency audit, HTTPS/reverse proxy, service lifecycle, resource/request limits, safe logging (queries are in URLs), monitoring and deployment-specific tests. Do not run as root or publicly bind the Flask development server. No Linux server, Render or Cloudflare configuration is changed here.

## API contract

- `GET /` — responsive demo interface and synthetic-data notice.
- `GET /ask?q=kitchen+printer+offline` — HTTP 200, `answer`, `matched_section`, and up to three ranked `sources` containing `section`, `file`, and `score`.
- Missing, empty or whitespace-only `q` — HTTP 400, `{"error": "empty query"}`.
- No acceptable lexical match — HTTP 200, `{"answer": "No matching knowledge base entries.", "sources": []}`. This does not mean the underlying issue has no solution.

Do not submit private customer, payment, employee or company information. This GET endpoint puts the query in the URL, which browsers and infrastructure may retain.

## Tests and CI

```bash
python -m pip check
python -B -m unittest discover -s tests -v
```

The standard-library test suite covers title weighting, introduction exclusion, Unicode handling, common-word/unrelated-query rejection, known synthetic issues, result limits, the Flask API contract, homepage landmarks and non-debug loopback launch settings. No LLM or network service is required by the tests. These are regression examples, not an independent relevance benchmark or security audit. Browser interaction and responsive layout need separate verification; unit tests alone do not prove those.

`.github/workflows/tests.yml` configures the same tests for Python 3.11 and 3.14 on pushes and pull requests, using read-only repository permission and SHA-pinned official actions. Configuration alone does not prove a successful GitHub run. Flask stays pinned in `requirements.txt`; transitive dependencies are not locked, and no dependency-security claim is made.

## Author

Anton Yarmilko - [LinkedIn](https://www.linkedin.com/in/anton-yarmilko/)
