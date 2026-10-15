import unittest
from slug import normalize_title


class SlugTest(unittest.TestCase):
    def test_simple_title(self):
        self.assertEqual('hello-world', normalize_title('Hello World'))

    def test_collapses_repeated_spaces(self):
        self.assertEqual('hello-world', normalize_title('Hello   World'))

    def test_collapses_tabs_and_mixed_whitespace(self):
        for title in ('Hello\tWorld', 'Hello \t \tWorld', 'Hello\n\rWorld',
                      'Hello\u00a0\u2003World'):
            with self.subTest(title=title):
                self.assertEqual('hello-world', normalize_title(title))

    def test_empty_and_all_whitespace(self):
        for title in ('', '   ', '\t\n\r', '\u00a0\u2003'):
            with self.subTest(title=title):
                self.assertEqual('', normalize_title(title))

    def test_strips_boundaries_and_lowercases_single_word(self):
        self.assertEqual('hello', normalize_title(' \tHeLLo\n '))

    def test_preserves_non_whitespace_characters(self):
        self.assertEqual('ticket-42:-fix_it!',
                         normalize_title('Ticket-42:  Fix_IT!'))
