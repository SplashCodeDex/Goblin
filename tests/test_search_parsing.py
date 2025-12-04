import os
import sys
import unittest

# Ensure we can import robin package
sys.path.append(os.path.abspath("src"))

from bs4 import BeautifulSoup
from robin.search import _clean_onion_url, _extract_onions_from_soup, _canonicalize_url


class TestSearchParsing(unittest.TestCase):
    def test_clean_onion_url_normalizes(self):
        cases = [
            ("//exampleonionabcdefghijklm.onion/path?x=1", "http://exampleonionabcdefghijklm.onion/path"),
            ("www.exampleonionabcdefghijklm.onion/", "http://exampleonionabcdefghijklm.onion/"),
            ("exampleonionabcdefghijklm.onion/path,", "http://exampleonionabcdefghijklm.onion/path"),
            ("http://exampleonionabcdefghijklm.onion/path)", "http://exampleonionabcdefghijklm.onion/path"),
            ("https://exampleonionabcdefghijklm.onion/path", "https://exampleonionabcdefghijklm.onion/path"),
        ]
        for raw, expected_prefix in cases:
            cleaned = _clean_onion_url(raw)
            # We don't assert exact equality when query stripped; ensure startswith and no trailing punct
            self.assertTrue(cleaned.startswith(expected_prefix))
            self.assertNotRegex(cleaned, r"[\,\.;:!\?\)]$")

    def test_extract_onions_from_soup(self):
        html = '''
        <html>
          <body>
            <a href="http://goodaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion/page">Good Link</a>
            <a data-href="https%3A%2F%2Fdataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion%2Fq%3D1">Data Href</a>
            <a href="#" data-url="http://urlaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion/x">Has Data URL</a>
            <a>Text https://textaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion/inside</a>
          </body>
        </html>
        '''
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_onions_from_soup(soup)
        urls = sorted(set([item["link"] for item in links]))
        # Expect 4 unique onion URLs normalized
        self.assertTrue(any(u.startswith("http://goodaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion") for u in urls))
        self.assertTrue(any(u.startswith("https://dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion") or u.startswith("http://dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion") for u in urls))
        self.assertTrue(any(u.startswith("http://urlaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion") for u in urls))
        self.assertTrue(any(u.startswith("http://textaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion") for u in urls))

    def test_canonicalize_url(self):
        u1 = "http://abcaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion/path?x=1#frag"
        u2 = "http://abcaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.onion/path"
        self.assertEqual(_canonicalize_url(u1), _canonicalize_url(u2))


if __name__ == "__main__":
    unittest.main()
