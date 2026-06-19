import re
from unidecode import unidecode


def normalize(text: str) -> str:
    """Convierte texto a forma canónica: mayúsculas, sin tildes ni caracteres especiales."""
    if not text:
        return ""
    result = unidecode(text.strip().upper())
    result = re.sub(r"[^A-Z0-9\s]", "", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result
