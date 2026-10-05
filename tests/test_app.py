import unittest
import runpy
from pathlib import Path
from unittest.mock import patch

from app import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_identifies_content_as_synthetic(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"synthetic", response.data.lower())

    def test_home_exposes_accessible_search_and_result_regions(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="viewport"', page)
        self.assertIn('for="query"', page)
        self.assertIn('id="answer"', page)
        self.assertIn('id="sources"', page)
        self.assertIn('role="status"', page)
        self.assertIn('Do not enter private', page)

    def test_direct_local_launch_disables_debugger_and_reloader(self):
        from flask import Flask

        with patch.object(Flask, "run") as run:
            runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.py"), run_name="__main__")
        run.assert_called_once_with(host="127.0.0.1", port=5081, debug=False, use_reloader=False)

    def test_matching_query_returns_verbatim_answer_and_ranked_sources(self):
        from rag import load_sections

        response = self.client.get("/ask", query_string={"q": "kitchen printer offline"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["matched_section"], "Kitchen printer offline")
        expected = next(s for s in load_sections() if s["title"] == data["matched_section"])
        self.assertEqual(data["answer"], expected["body"].strip())
        self.assertEqual(data["sources"][0]["section"], data["matched_section"])
        self.assertTrue(all(s["file"] == "pos_troubleshooting.md" for s in data["sources"]))
        scores = [s["score"] for s in data["sources"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertLessEqual(len(scores), 3)

    def test_missing_or_blank_query_is_bad_request(self):
        for args in ({}, {"q": ""}, {"q": "   "}):
            with self.subTest(args=args):
                response = self.client.get("/ask", query_string=args)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json(), {"error": "empty query"})

    def test_no_match_queries_return_no_sources_or_invented_answer(self):
        queries = ["zzzxxyy", "the", "!!!", "кухонний принтер не працює", "printer mortgage bankruptcy"]
        for query in queries:
            with self.subTest(query=query):
                response = self.client.get("/ask", query_string={"q": query})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(), {
                    "answer": "No matching knowledge base entries.", "sources": [],
                })
