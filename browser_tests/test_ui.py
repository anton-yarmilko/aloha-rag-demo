"""Opt-in Chromium regressions; separate from dependency-free API tests."""
from contextlib import ExitStack
from pathlib import Path
import json
import sys
from threading import Thread
import unittest

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import WSGIRequestHandler, make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app


class QuietHandler(WSGIRequestHandler):
    def log_request(self, code="-", size="-"):
        pass


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        resources = ExitStack()
        cls.addClassCleanup(resources.close)
        server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
        resources.callback(server.server_close)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        resources.callback(thread.join, timeout=5)
        resources.callback(server.shutdown)
        cls.base_url = f"http://127.0.0.1:{server.server_port}"
        playwright = sync_playwright().start()
        resources.callback(playwright.stop)
        cls.browser = playwright.chromium.launch()
        resources.callback(cls.browser.close)

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 900})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.page_errors = []
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        self.page.goto(self.base_url)

    def tearDown(self):
        self.assertEqual(self.page_errors, [], "Unexpected JavaScript errors")

    def search(self, query="kitchen printer offline"):
        self.page.get_by_label("Describe a demo issue in English").fill(query)
        self.page.get_by_role("button", name="Search knowledge").click()

    def expected_answer(self):
        response = self.context.request.get(self.base_url + "/ask", params={"q": "kitchen printer offline"})
        self.assertEqual(response.status, 200)
        return response.json()

    def test_success_displays_verbatim_answer_and_ranked_sources(self):
        data = self.expected_answer()
        self.search()
        expect(self.page.get_by_role("status")).to_contain_text("Retrieved a synthetic source excerpt")
        self.assertEqual(self.page.locator("#answer").text_content(), data["answer"])
        self.assertEqual(self.page.locator("#matched-section").text_content(), data["matched_section"])
        expected_sources = [f'{s["section"]} · {s["file"]} · score {s["score"]}' for s in data["sources"]]
        self.assertEqual(self.page.locator("#sources li").all_text_contents(), expected_sources)
        expect(self.page.get_by_text("Lexical ranking scores are not confidence or probability.")).to_be_visible()

    def test_no_match_clears_previous_answer(self):
        self.search()
        expect(self.page.locator("#result")).to_be_visible()
        self.search("zzzxxyy")
        expect(self.page.get_by_role("status")).to_contain_text("No matching knowledge base entries")
        expect(self.page.locator("#result")).to_be_hidden()
        expect(self.page.locator("#sources li")).to_have_count(0)
        self.assertEqual(self.page.locator("#answer").text_content(), "")

    def test_http_and_malformed_response_errors_allow_retry(self):
        cases = [(503, "unavailable"), (200, "not json"), (200, '{"answer":42,"sources":[]}')]
        for status, body in cases:
            with self.subTest(status=status, body=body):
                self.page.route("**/ask?*", lambda route: route.fulfill(status=status, content_type="application/json", body=body))
                self.search()
                expect(self.page.get_by_role("status")).to_contain_text("Could not load an answer")
                expect(self.page.locator("#result")).to_be_hidden()
                expect(self.page.get_by_role("button", name="Search knowledge")).to_be_enabled()
                self.page.unroute("**/ask?*")
                self.search()
                expect(self.page.locator("#result")).to_be_visible()

    def test_empty_and_whitespace_queries_do_not_send_requests(self):
        requests = []
        self.page.on("request", lambda request: requests.append(request.url) if "/ask?" in request.url else None)
        self.search("")
        self.assertFalse(self.page.get_by_label("Describe a demo issue in English").evaluate("input => input.checkValidity()"))
        self.search("   ")
        expect(self.page.get_by_role("status")).to_have_text("Enter a demo issue before searching.")
        expect(self.page.get_by_label("Describe a demo issue in English")).to_be_focused()
        self.assertEqual(requests, [])

    def test_network_failure_allows_retry_without_stale_answer(self):
        self.search()
        expect(self.page.locator("#result")).to_be_visible()
        self.page.route("**/ask?*", lambda route: route.abort("internetdisconnected"))
        self.search()
        expect(self.page.get_by_role("status")).to_contain_text("Could not load an answer")
        expect(self.page.locator("#result")).to_be_hidden()
        expect(self.page.get_by_role("button", name="Search knowledge")).to_be_enabled()
        self.page.unroute("**/ask?*")
        self.search()
        expect(self.page.locator("#result")).to_be_visible()

    def test_loading_disables_submit_then_timeout_allows_retry(self):
        self.page.clock.install()
        pending = []
        self.page.route("**/ask?*", lambda route: pending.append(route))
        with self.page.expect_request("**/ask?*"):
            self.search()
        expect(self.page.get_by_role("status")).to_have_text("Searching the local knowledge base…")
        expect(self.page.get_by_role("button", name="Search knowledge")).to_be_disabled()
        expect(self.page.locator("#result")).to_be_hidden()
        self.page.clock.fast_forward(15001)
        expect(self.page.get_by_role("status")).to_have_text("Search timed out. Please try again.")
        expect(self.page.get_by_role("button", name="Search knowledge")).to_be_enabled()
        self.assertEqual(len(pending), 1)
        pending[0].abort()
        self.page.unroute("**/ask?*")
        self.search()
        expect(self.page.locator("#result")).to_be_visible()

    def test_retrieved_markup_is_displayed_as_text(self):
        markup = '<img src="data:," onerror="window.alohaInjected=true">'
        data = {"answer": markup, "matched_section": markup, "sources": [
            {"section": markup, "file": markup, "score": 0.5},
        ]}
        self.page.route("**/ask?*", lambda route: route.fulfill(json=data))
        self.search()
        expect(self.page.locator("#result")).to_be_visible()
        self.assertEqual(self.page.locator("#answer").text_content(), markup)
        self.assertEqual(self.page.locator("#matched-section").text_content(), markup)
        self.assertIn(markup, self.page.locator("#sources").text_content())
        expect(self.page.locator("#result img")).to_have_count(0)
        self.assertIsNone(self.page.evaluate("window.alohaInjected"))

    def test_keyboard_search_and_responsive_layout(self):
        for width, height in [(1280, 900), (390, 844)]:
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": height})
                field = self.page.get_by_label("Describe a demo issue in English")
                field.fill("kitchen printer offline")
                field.press("Enter")
                expect(self.page.locator("#result")).to_be_visible()
                self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth"))
                bounds = self.page.get_by_role("button", name="Search knowledge").bounding_box()
                self.assertIsNotNone(bounds)
                self.assertGreaterEqual(bounds["x"], 0)
                self.assertLessEqual(bounds["x"] + bounds["width"], width)

    def test_without_javascript_form_opens_json_api(self):
        context = self.browser.new_context(java_script_enabled=False)
        self.addCleanup(context.close)
        page = context.new_page()
        page.goto(self.base_url)
        expect(page.get_by_role("button", name="Search knowledge")).to_be_visible()
        page.get_by_label("Describe a demo issue in English").fill("kitchen printer offline")
        with page.expect_navigation() as navigation:
            page.get_by_role("button", name="Search knowledge").click()
        self.assertEqual(navigation.value.status, 200)
        self.assertIn("/ask?q=kitchen", page.url)
        self.assertEqual(json.loads(page.locator("body").inner_text()), self.expected_answer())


if __name__ == "__main__":
    unittest.main()
