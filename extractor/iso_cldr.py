# extractor/iso_cldr.py
import pandas as pd
import requests
from pathlib import Path

ISO_URLS = {
    "iso-639-3.tab": "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab",
    "iso-639-3_Name_Index.tab": "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3_Name_Index.tab"
}

def download_if_missing(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    for fname, url in ISO_URLS.items():
        fpath = path / fname
        if not fpath.exists():
            print(f"⬇️  Downloading {fname} from SIL…")
            r = requests.get(url)
            r.raise_for_status()
            fpath.write_bytes(r.content)
            print(f"✅ Saved to {fpath}")

def load_iso_tables(path: Path):
    """
    Load ISO 639-3 data; auto-download if missing.
    
    IMPORTANT: keep_default_na=False prevents 'nan' from being interpreted as NaN
    (nan_Latn is a valid language code for Min Nan / Southern Min!)
    
    Why this matters:
    - ISO 639-3 code 'nan' = Min Nan language (spoken in Taiwan, Fujian)
    - Pandas by default converts 'nan', 'NA', 'null' strings to NaN
    - This breaks our code when processing nan_Latn
    
    Solution: keep_default_na=False, na_values=[''] (only empty strings are NaN)
    """
    download_if_missing(path)
    
    # Read with explicit NaN handling
    iso = pd.read_csv(
        path / "iso-639-3.tab", 
        sep="\t",
        keep_default_na=False,  # Don't auto-convert 'nan' to NaN
        na_values=[''],         # Only empty strings are NaN
        dtype=str               # Keep everything as strings
    )
    
    names = pd.read_csv(
        path / "iso-639-3_Name_Index.tab", 
        sep="\t",
        keep_default_na=False,
        na_values=[''],
        dtype=str
    )
    
    iso = iso.set_index("Id")
    return {"core": iso, "names": names}

def cldr_script_name(script_code: str, cldr_root: Path) -> str:
    # simple static map fallback if needed
    # (CLDR JSON lookups can be added here)
    return script_code