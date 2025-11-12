# extractor/supported.py
from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import json
import importlib

FALLBACK_FILES = [
    Path("sources/supported_langs.txt"),   # one code per line
    Path("sources/supported_langs.json"),  # ["hin_Deva", "eng_Latn", ...]
]

def load_supported_codes() -> List[str]:
    """
    Try to import Omnilingual ASR's supported_langs.
    Fallback to local files in sources/ if the import isn't available.
    """
    # 1) Try import from the package
    try:
        mod = importlib.import_module("omnilingual_asr.models.wav2vec2_llama.lang_ids")
        codes = getattr(mod, "supported_langs", None)
        if codes and isinstance(codes, (list, tuple)):
            return list(codes)
    except Exception:
        pass

    # 2) Try local files (txt or json)
    for f in FALLBACK_FILES:
        if f.exists():
            if f.suffix == ".txt":
                return [line.strip() for line in f.read_text().splitlines() if line.strip()]
            if f.suffix == ".json":
                return json.loads(f.read_text())

    raise RuntimeError(
        "Could not load supported language codes. "
        "Install omnilingual_asr OR provide sources/supported_langs.txt or .json"
    )
