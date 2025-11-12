# scripts/build_index.py
from __future__ import annotations
import json, unicodedata, re
from pathlib import Path
from typing import Dict, List, Set

SRC = Path("data/languages.json")
OUT = Path("data/finder_index.json")

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    s = s.strip()
    return s

def add(m: Dict[str, List[str]], k: str, v: str):
    if not k: return
    k = norm(k)
    if not k: return
    m.setdefault(k, [])
    if v not in m[k]:
        m[k].append(v)

def main():
    data = json.loads(SRC.read_text())
    by_name: Dict[str, List[str]] = {}
    by_autonym: Dict[str, List[str]] = {}
    by_alias: Dict[str, List[str]] = {}
    by_iso3: Dict[str, List[str]] = {}
    by_glotto: Dict[str, str] = {}
    by_script: Dict[str, List[str]] = {}
    by_country: Dict[str, List[str]] = {}
    by_region: Dict[str, List[str]] = {}
    meta_codes: Dict[str, Dict] = {}

    for code, row in data.items():
        iso3 = row.get("iso_639_3")
        script = row.get("script_code") or (row.get("script_name", {}) or {}).get("value")
        script_norms = set()
        if script:
            script_norms.add(norm(script))
        # also include common aliases for script
        script_map = {"devanagari":"deva", "deva":"deva", "latin":"latn", "latn":"latn", "arabic":"arab", "arab":"arab"}
        for s in list(script_norms):
            if s in script_map:
                script_norms.add(script_map[s])

        # names
        en_name = (row.get("english_name") or {}).get("value") or row.get("english_name") or ""
        autonym = (row.get("autonym") or {}).get("value") if isinstance(row.get("autonym"), dict) else row.get("autonym")
        wiki = (row.get("wikipedia_code") or {}).get("value")

        # geo
        countries_iso2 = row.get("primary_countries") or (row.get("provenance",{}).get("geo",{}).get("countries_iso2") or [])
        regions = row.get("regions") or (row.get("provenance",{}).get("geo",{}).get("regions") or [])

        # indexes
        if en_name: add(by_name, en_name, code)
        if autonym: add(by_autonym, autonym, code)
        if wiki: add(by_alias, wiki, code)

        if iso3: add(by_iso3, iso3, code)
        gl = (row.get("glottolog_code") or {}).get("value") if isinstance(row.get("glottolog_code"), dict) else row.get("glottolog_code")
        if gl:
            by_glotto[norm(gl)] = code

        for s in script_norms:
            add(by_script, s, code)

        for c in countries_iso2:
            add(by_country, c, code)
        # country labels sometimes appear in regions; also index ISO2 again as lowercase
        for c in countries_iso2:
            add(by_country, c.lower(), code)

        for r in regions:
            add(by_region, r, code)

        # tiny meta for tie-breaking
        meta_codes[code] = {
            "script": row.get("script_code") or (row.get("script_name") or {}).get("value"),
            "countries": countries_iso2,
            "iso3": iso3
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "by_name": by_name,
        "by_autonym": by_autonym,
        "by_alias": by_alias,
        "by_iso3": by_iso3,
        "by_glotto": by_glotto,
        "by_script": by_script,
        "by_country": by_country,
        "by_region": by_region,
        "meta": { "codes": meta_codes }
    }, ensure_ascii=False, indent=2))
    print(f"Built index → {OUT}")

if __name__ == "__main__":
    main()
