import unittest

from rag import load_sections, search


class SearchTests(unittest.TestCase):
    def test_title_terms_are_weighted_without_merging_words(self):
        sections = [
            {"title": "Alpha beta", "body": "filler " * 8, "source": "demo.md"},
            {"title": "Other", "body": "beta " * 2 + "filler " * 8, "source": "demo.md"},
        ]
        self.assertEqual(search("beta", sections)[0]["title"], "Alpha beta")

    def test_loader_excludes_document_intro_from_answers(self):
        sections = load_sections()
        self.assertEqual(len(sections), 5)
        self.assertTrue(all(sec["title"] != "pos_troubleshooting" for sec in sections))

    def test_common_words_alone_do_not_return_instructions(self):
        self.assertEqual(search("the and is", load_sections()), [])

    def test_incidental_overlap_does_not_answer_unrelated_query(self):
        self.assertEqual(search("printer mortgage bankruptcy", load_sections()), [])

    def test_unsupported_words_are_not_discarded_to_create_a_false_match(self):
        self.assertEqual(search("printer іпотека банкрутство", load_sections()), [])

    def test_each_synthetic_issue_ranks_its_own_answer_first(self):
        sections = load_sections()
        for section in sections:
            with self.subTest(title=section["title"]):
                self.assertEqual(search(section["title"], sections)[0]["title"], section["title"])

    def test_unicode_query_matches_unicode_content_without_translation(self):
        sections = [{"title": "Принтер", "body": "Синтетичний приклад", "source": "demo.md"}]
        self.assertEqual(search("ПРИНТЕР", sections)[0]["title"], "Принтер")

    def test_empty_input_or_empty_index_has_no_matches(self):
        for query, sections in [("", load_sections()), ("!!!", load_sections()), ("printer", [])]:
            with self.subTest(query=query):
                self.assertEqual(search(query, sections), [])

    def test_top_k_limits_results_and_zero_returns_none(self):
        sections = load_sections()
        self.assertEqual(len(search("kitchen", sections, top_k=1)), 1)
        self.assertEqual(search("kitchen", sections, top_k=0), [])
