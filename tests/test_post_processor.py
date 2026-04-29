"""
Test suite for the Markdown Post-Processor

Tests cover:
- URL garbling fixes
- DOI splitting fixes
- Math formula fixes
- OCR error corrections
- Reference formatting
- Heading artifact fixes
"""

import unittest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Execution.processors.post_processor import MarkdownPostProcessor, post_process_markdown


class TestURLFixes(unittest.TestCase):
    """Test URL garbling fixes"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_subset_to_question_mark(self):
        """Test fixing $\\subset$ -> ? in URLs"""
        content = "Visit http://example.com$\\subset$id=123"
        result = self.processor.process(content)
        self.assertIn("http://example.com?id=123", result)
    
    def test_acm_citation_url(self):
        """Test fixing ACM citation URLs"""
        content = "http://dl.acm.org/citation.cfm$\\subset$id=795666.796607"
        result = self.processor.process(content)
        self.assertIn("http://dl.acm.org/citation.cfm?id=795666.796607", result)
    
    def test_doi_url_intact(self):
        """Test that DOI URLs remain intact"""
        content = "https://doi.org/10.1145/3197517.3201381"
        result = self.processor.process(content)
        self.assertIn("https://doi.org/10.1145/3197517.3201381", result)
    
    def test_markdown_link_url_fix(self):
        """Test fixing URLs inside markdown links"""
        content = "[Link](http://example.com$\\subset$foo=bar)"
        result = self.processor.process(content)
        self.assertIn("](http://example.com?foo=bar)", result)


class TestDOIFixes(unittest.TestCase):
    """Test DOI splitting fixes"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_split_doi_with_space(self):
        """Test fixing DOIs split with space"""
        content = "https://doi.org/10.1145/3197517. 3201381"
        result = self.processor.process(content)
        self.assertIn("https://doi.org/10.1145/3197517.3201381", result)
    
    def test_split_https(self):
        """Test fixing split https://"""
        content = "https: //doi.org/10.1145/123456"
        result = self.processor.process(content)
        self.assertIn("https://doi.org/10.1145/123456", result)


class TestMathFixes(unittest.TestCase):
    """Test math formula fixes"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_math_spacing_subscript(self):
        """Test fixing excessive spacing in subscripts"""
        content = "$d _ { e }$"
        result = self.processor.process(content)
        self.assertIn("$d_{e}$", result)
    
    def test_math_spacing_superscript(self):
        """Test fixing excessive spacing in superscripts"""
        content = "$x ^ { 2 }$"
        result = self.processor.process(content)
        self.assertIn("$x^{2}$", result)
    
    def test_mathcal_spacing(self):
        """Test fixing \\mathcal spacing"""
        content = "$\\mathcal { M }$"
        result = self.processor.process(content)
        self.assertIn("$\\mathcal{M}$", result)
    
    def test_copyright_in_math_mode(self):
        """Test fixing copyright symbol incorrectly in math mode"""
        content = "$\\mathbb{C} 1 9 9 5$"
        result = self.processor.process(content)
        self.assertIn("©1995", result)
    
    def test_spaced_decimal(self):
        """Test fixing spaced decimals like 0. 2 5"""
        content = "$x = 0. 2 5$"
        result = self.processor.process(content)
        self.assertIn("0.25", result)
    
    def test_pmb_to_mathbf(self):
        """Test converting verbose \\pmb notation"""
        content = "$\\pmb { p }$"
        result = self.processor.process(content)
        self.assertIn("$\\mathbf{p}$", result)
    
    def test_dot_minus_fix(self):
        """Test fixing malformed \\dot{-} to proper minus"""
        content = "$P = 1 \\dot { - } 0.2$"
        result = self.processor.process(content)
        self.assertIn("-", result)
        self.assertNotIn("\\dot", result)


class TestMathValidation(unittest.TestCase):
    """Test math validation"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_detect_unbalanced_braces(self):
        """Test detection of unbalanced braces"""
        content = "$\\frac{1}{2$"
        issues = self.processor.validate_math(content)
        self.assertTrue(any("Unbalanced braces" in i['issue'] for i in issues))
    
    def test_valid_math_passes(self):
        """Test that valid math has no issues"""
        content = "$\\frac{1}{d_e^2 + \\epsilon}$"
        issues = self.processor.validate_math(content)
        self.assertEqual(len(issues), 0)


class TestOCRFixes(unittest.TestCase):
    """Test OCR error fixes"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_ligature_fi(self):
        """Test fixing fi ligature"""
        content = "ﬁnding the ﬁrst"
        result = self.processor.process(content)
        self.assertIn("finding the first", result)
    
    def test_ligature_fl(self):
        """Test fixing fl ligature"""
        content = "ﬂow ﬂuid"
        result = self.processor.process(content)
        self.assertIn("flow fluid", result)
    
    def test_smart_quotes(self):
        """Test normalizing smart quotes"""
        content = '\u201cquoted\u201d and \u2018single\u2019'
        result = self.processor.process(content)
        self.assertIn('"quoted"', result)
        self.assertIn("'single'", result)


class TestReferenceFixes(unittest.TestCase):
    """Test reference formatting fixes"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_reference_section_detected(self):
        """Test that references section is detected and concatenated refs split"""
        content = """
# REFERENCES

Smith, J. 2020. First Paper Title. Journal. https://doi.org/10.1234/5678Jones, A. 2021. Second Paper. Conference.
"""
        result = self.processor.process(content)
        # Should have split at URL end before new author
        # The URL should be followed by newline(s) before the next reference
        self.assertIn("https://doi.org/10.1234/5678", result)
        self.assertIn("Jones, A. 2021", result)


class TestHeadingFixes(unittest.TestCase):
    """Test heading artifact fixes"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_doi_heading_fix(self):
        """Test fixing DOI fragments that became headings"""
        content = """
Some text.

# 1109/TVCG.2003.1260744

More text.
"""
        result = self.processor.process(content)
        self.assertNotIn("# 1109/TVCG", result)


class TestWhitespaceCleanup(unittest.TestCase):
    """Test whitespace cleanup"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_trailing_whitespace_removed(self):
        """Test removal of trailing whitespace"""
        content = "Line with trailing spaces   \nNext line"
        result = self.processor.process(content)
        self.assertNotIn("   \n", result)
    
    def test_multiple_blank_lines_normalized(self):
        """Test normalization of multiple blank lines"""
        content = "Paragraph 1\n\n\n\n\n\nParagraph 2"
        result = self.processor.process(content)
        self.assertNotIn("\n\n\n\n", result)
    
    def test_space_before_punctuation_fixed(self):
        """Test fixing spaces before punctuation"""
        content = "Hello , world ."
        result = self.processor.process(content)
        self.assertIn("Hello, world.", result)


class TestIntegration(unittest.TestCase):
    """Integration tests with real-world examples"""
    
    def setUp(self):
        self.processor = MarkdownPostProcessor()
    
    def test_complex_academic_content(self):
        """Test processing complex academic content"""
        content = """
# Volume-Aware Design

The formula is $d _ { e }$ where $\\mathcal { M }$ is the surface.

See https://doi.org/10.1145/3197517. 3201381 for details.

Also http://dl.acm.org/citation.cfm$\\subset$id=795666.796607

# REFERENCES

Author One. 2020. Paper One. https://doi.org/10.1234/5678
Author Two. 2021. Paper Two. https://doi.org/10.5678/1234
"""
        result = self.processor.process(content)
        
        # Check all fixes applied
        self.assertIn("$d_{e}$", result)
        self.assertIn("$\\mathcal{M}$", result)
        self.assertIn("https://doi.org/10.1145/3197517.3201381", result)
        self.assertIn("?id=795666.796607", result)
        # DOIs should remain intact (not converted to fractions)
        self.assertIn("https://doi.org/10.1234/5678", result)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestURLFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestDOIFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestMathFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestMathValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestOCRFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestReferenceFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestHeadingFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestWhitespaceCleanup))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
