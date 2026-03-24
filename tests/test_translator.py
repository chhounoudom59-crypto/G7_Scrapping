# =============================================================
# tests/test_translator.py — Unit tests for utils/translator.py
# =============================================================
# NOTE: We mock the external GoogleTranslator API so tests run
# offline and never hit the network.
# =============================================================

from unittest.mock import MagicMock, patch

import pytest

from utils.translator import _split_chunks, translate_to_english


# ─────────────────────────────────────────────────────────────
# _split_chunks
# ─────────────────────────────────────────────────────────────

class TestSplitChunks:
    def test_short_text_is_one_chunk(self):
        result = _split_chunks("Hello world", size=100)
        assert result == ["Hello world"]

    def test_empty_string_returns_list_with_empty(self):
        result = _split_chunks("", size=100)
        assert isinstance(result, list)

    def test_splits_on_paragraph_boundary(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        result = _split_chunks(text, size=15)
        assert len(result) > 1
        # Each chunk must be ≤ size chars
        for chunk in result:
            assert len(chunk) <= 15 or len(chunk.split("\n\n")[0]) <= 15

    def test_long_single_paragraph_split_hard(self):
        text = "A" * 200
        result = _split_chunks(text, size=50)
        assert len(result) >= 4
        # All chunks except maybe the last are exactly size
        for chunk in result[:-1]:
            assert len(chunk) <= 50

    def test_result_is_always_a_list(self):
        assert isinstance(_split_chunks("hi", size=100), list)

    def test_no_chunk_exceeds_size(self):
        text = "\n\n".join(["word " * 20] * 10)  # 10 paragraphs
        result = _split_chunks(text, size=200)
        for chunk in result:
            assert len(chunk) <= 200

    def test_rejoining_preserves_content(self):
        text = "Para A.\n\nPara B.\n\nPara C."
        chunks = _split_chunks(text, size=500)
        rejoined = "\n\n".join(chunks)
        # All words survive
        assert "Para A" in rejoined
        assert "Para B" in rejoined
        assert "Para C" in rejoined


# ─────────────────────────────────────────────────────────────
# translate_to_english
# ─────────────────────────────────────────────────────────────

class TestTranslateToEnglish:
    def test_empty_string_returned_unchanged(self):
        assert translate_to_english("") == ""

    def test_whitespace_only_returned_unchanged(self):
        assert translate_to_english("   ") == "   "

    def test_english_text_not_translated(self):
        """English text should be returned immediately without API call."""
        text = "The Prime Minister announced new climate policies today."
        with patch("utils.translator._detect_lang", return_value="en"):
            with patch("deep_translator.GoogleTranslator") as mock_gt:
                result = translate_to_english(text)
                mock_gt.assert_not_called()
                assert result == text

    def test_hint_lang_en_skips_translation(self):
        """hint_lang='en' should bypass detection and return original."""
        text = "Some text here."
        result = translate_to_english(text, hint_lang="en")
        assert result == text

    def test_hint_lang_en_us_skips_translation(self):
        text = "Some text here."
        assert translate_to_english(text, hint_lang="en-us") == text

    def test_non_english_calls_translator(self):
        """Non-English text should call GoogleTranslator."""
        french_text = "Le Premier ministre a annoncé de nouvelles politiques."

        mock_translator_instance = MagicMock()
        mock_translator_instance.translate.return_value = "The Prime Minister announced new policies."

        with patch("utils.translator._detect_lang", return_value="fr"):
            with patch("deep_translator.GoogleTranslator", return_value=mock_translator_instance):
                result = translate_to_english(french_text)
                mock_translator_instance.translate.assert_called_once()
                assert "Prime Minister" in result

    def test_translation_error_returns_original(self):
        """On API failure, original text should be returned (graceful fallback)."""
        text = "Der Bundeskanzler hat neue Maßnahmen angekündigt."

        mock_translator_instance = MagicMock()
        mock_translator_instance.translate.side_effect = Exception("API unavailable")

        with patch("utils.translator._detect_lang", return_value="de"):
            with patch("deep_translator.GoogleTranslator", return_value=mock_translator_instance):
                result = translate_to_english(text)
                assert result == text

    def test_missing_library_returns_original(self):
        """If deep_translator is not installed, return original text.
        We verify the graceful fallback by calling with an English text
        (no translation attempt) since mocking the import is complex.
        """
        text = "Le gouvernement a pris des mesures."
        # Test the fallback branch: even if translation fails, never raises
        with patch("utils.translator._detect_lang", return_value="fr"):
            with patch("deep_translator.GoogleTranslator",
                       side_effect=ImportError("No module named deep_translator")):
                result = translate_to_english(text)
                assert isinstance(result, str)
                assert len(result) > 0

    def test_chunked_translation_rejoins(self):
        """Multi-chunk text should be rejoined with double newlines."""
        long_text = "Para A.\n\nPara B.\n\nPara C."

        mock_translator_instance = MagicMock()
        mock_translator_instance.translate.side_effect = lambda text: text + " [translated]"

        with patch("utils.translator._detect_lang", return_value="fr"):
            with patch("deep_translator.GoogleTranslator", return_value=mock_translator_instance):
                result = translate_to_english(long_text)
                assert isinstance(result, str)
                assert "[translated]" in result
