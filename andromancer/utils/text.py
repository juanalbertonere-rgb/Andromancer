import unicodedata

def normalize_text(text: str) -> str:
    """Removes accents and converts to lowercase."""
    if not text:
        return ""
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
