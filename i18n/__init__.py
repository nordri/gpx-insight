import json
from pathlib import Path


DEFAULT_LANG = "es"
_I18N_DIR = Path(__file__).resolve().parent
TRANSLATIONS = {
    lang: json.loads((_I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    for lang in ("es", "en")
}
