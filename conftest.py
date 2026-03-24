# =============================================================
# conftest.py — Shared pytest fixtures for all test modules
# =============================================================

import os
import sys

import pytest

# Make project root importable (same as how main.py does it)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ── Minimal HTML fixtures ─────────────────────────────────────

@pytest.fixture
def simple_article_html() -> str:
    """A clean, minimal article HTML page for parser tests."""
    return """
    <html>
    <head><title>Test Article Title</title></head>
    <body>
      <main>
        <h1>Test Article Title</h1>
        <time datetime="2026-03-24">March 24, 2026</time>
        <article>
          <p>This is the body of the article. It contains enough content to pass
          the minimum length check. Here is some more text to make it longer than
          three hundred characters so the parser does not skip it as thin content.
          Government policy decisions are important for economic stability and growth.
          The ministers discussed several key topics at the summit meeting today.</p>
        </article>
      </main>
    </body>
    </html>
    """


@pytest.fixture
def thin_article_html() -> str:
    """HTML with content that's too short — parser should return None."""
    return """
    <html><body><main><p>Short.</p></main></body></html>
    """


@pytest.fixture
def minimal_selectors() -> dict:
    """Minimal scraper selectors used in parser tests."""
    return {
        "title": "h1",
        "date": "time",
        "date_attr": "datetime",
        "body": "article, main",
        "article_links": "a",
    }
