# =============================================================
# utils/translator.py — Auto-translate to English
# =============================================================
# Uses Google Translate (via deep-translator, no API key needed).
# Detects the language first with langdetect; if already English
# the text is returned unchanged immediately (zero cost, zero delay).
#
# CHUNKING: Google Translate has a ~5000 char limit per request.
# Long bodies are split on paragraph boundaries, translated in
# chunks, and re-joined — so nothing gets truncated.
# =============================================================

from utils.logger import get_logger

log = get_logger(__name__)

# Maximum characters per translate API call (Google limit is ~5000)
_CHUNK_SIZE = 4500


def _detect_lang(text: str) -> str:
    """Return ISO-639-1 language code, or 'en' on any error."""
    try:
        from langdetect import detect
        return detect(text[:1000])          # sample first 1000 chars — fast
    except Exception:
        return "en"                          # assume English on failure


def _split_chunks(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    """
    Split text into chunks ≤ `size` chars, breaking on blank lines
    (\n\n paragraph boundaries) rather than mid-sentence.
    """
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = (current + "\n\n" + para).lstrip("\n") if current else para
        if len(candidate) <= size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If a single paragraph is too long, split it hard
            while len(para) > size:
                chunks.append(para[:size])
                para = para[size:]
            current = para

    if current:
        chunks.append(current)

    return chunks or [text]


def translate_to_english(text: str, hint_lang: str = "") -> str:
    """
    Translate `text` to English.  Returns the original if:
      • the text is already English
      • the translation library is unavailable
      • any network/API error occurs (graceful fallback)

    Args:
        text:       The text to translate (title or body).
        hint_lang:  Optional ISO language code hint (e.g. "fr", "de").
                    If provided, language detection is skipped.
    """
    if not text or not text.strip():
        return text

    # ── Language detection ────────────────────────────────────
    lang = hint_lang.lower() if hint_lang else _detect_lang(text)
    if lang in ("en", "en-us", "en-gb"):
        return text                          # already English — skip API call

    log.info(f"   Translating ({lang} → en) — {len(text)} chars")

    try:
        from deep_translator import GoogleTranslator

        chunks  = _split_chunks(text)
        translated_chunks: list[str] = []

        for i, chunk in enumerate(chunks, 1):
            if not chunk.strip():
                translated_chunks.append(chunk)
                continue
            try:
                result = GoogleTranslator(source="auto", target="en").translate(chunk)
                translated_chunks.append(result or chunk)
            except Exception as e:
                log.warning(f"    Chunk {i}/{len(chunks)} translation failed: {e} — keeping original")
                translated_chunks.append(chunk)

        translated = "\n\n".join(translated_chunks)
        log.info(f"   Translation done → {len(translated)} chars")
        return translated

    except ImportError:
        log.warning("  deep-translator not installed — skipping translation. Run: pip install deep-translator")
        return text
    except Exception as e:
        log.warning(f"  Translation error: {e} — keeping original text")
        return text
