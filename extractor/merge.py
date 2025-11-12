# extractor/merge.py
from datetime import datetime
from typing import Dict

def _resource_level_from_speakers(n: int | None) -> str:
    if n is None: return "low"
    if n >= 50_000_000: return "high"
    if n >= 1_000_000:  return "medium"
    return "low"

def _data_source_heuristic(iso3: str) -> str:
    # keep your earlier rule; make it overridable later
    high = {'hin','ben','tel','mar','tam','urd','guj','kan','mal','pan','ory','asm','nep'}
    return "both" if iso3 in high else "community"

def _related_by_family_geo_selfscript(this_code: str, all_langs: Dict[str, dict]) -> list[str]:
    me = all_langs[this_code]
    fam = (me.get("language_family") or {}).get("value")
    script = (me.get("script_name") or {}).get("value")
    countries = set(me.get("primary_countries") or [])
    # rank: same family + same script + shares any country, then by speakers desc
    scored = []
    for code, L in all_langs.items():
        if code == this_code: continue
        fam2 = (L.get("language_family") or {}).get("value")
        script2 = (L.get("script_name") or {}).get("value")
        if not fam2 or fam2 != fam: continue
        if script2 != script: continue
        if not countries.intersection(set(L.get("primary_countries") or [])): continue
        spk = (L.get("speaker_count") or {}).get("value") or 0
        scored.append(( -int(spk), code ))
    scored.sort()
    return [c for _, c in scored[:5]]


def _family_from_glottolog(gl: dict) -> str | None:
    """
    Walk Glottolog classification top→bottom and choose the most specific
    'family-like' node (often 2–4 levels from bottom). Fallback to the
    second-last if present.
    """
    if not gl or "classification" not in gl:
        return None
    chain = gl["classification"]
    # pick the penultimate family-ish level if possible (often the subfamily)
    names = [n.get("name") for n in chain if isinstance(n, dict) and n.get("name")]
    if not names:
        return None
    # heuristic: prefer a node that ends with "-Aryan", "Dravidian", "Sino-Tibetan", etc.
    preferred_suffixes = ["Aryan", "Dravidian", "Sino-Tibetan", "Austroasiatic",
                          "Indo-European", "Niger–Congo", "Afroasiatic", "Uralic",
                          "Turkic", "Austronesian", "Iranian", "Romance", "Germanic",
                          "Slavic", "Kartvelian", "Mande", "Nilotic"]
    for n in reversed(names):
        for suf in preferred_suffixes:
            if suf in n:
                return n
    # fallback: second-last if depth >= 2, else last
    return names[-2] if len(names) >= 2 else names[-1]

def val(v, source, conf):
    return {"value": v, "source": source, "confidence": conf, "last_updated": datetime.utcnow().isoformat()}

def merge_language(iso3, script_code, iso_tables, wd, glotto, cldr_map, geo=None):
    wdrow = wd.get(iso3, {})
    gl_code = wdrow.get("glottocode")
    gl = glotto.get(gl_code or "", {})

    family = _family_from_glottolog(gl)

    # geography
    countries_iso2 = []
    regions = []
    if geo and iso3 in geo:
        g = geo[iso3]
        countries_iso2 = g.get("countries_iso2") or []
        regions = g.get("regions") or []

    return {
        "code": f"{iso3}_{script_code}",
        "iso_639_3": iso3,
        "script_code": script_code,
        "english_name": val(iso_tables["core"].loc[iso3]["Ref_Name"], "iso639-3", 1.0),
        "autonym": val(wdrow.get("autonym"), "wikidata", 0.8) if wdrow.get("autonym") else None,
        "script_name": val(cldr_map.get(script_code, script_code), "cldr", 1.0),
        "writing_direction": val(("rtl" if script_code=="Arab" else "ltr"), "rule", 0.8),
        "language_family": val(family, "glottolog", 0.9) if family else None,
        "speaker_count": val(wdrow.get("speakers"), "wikidata", 0.6) if wdrow.get("speakers") else None,
        "primary_countries": countries_iso2 if countries_iso2 else [],
        "regions": regions,
        "coordinates": {"lat": gl.get("latitude"), "lon": gl.get("longitude")} if gl else None,
        "related_languages": [],  # filled below
        "wikipedia_code": val(wdrow.get("wikipedia"), "wikidata", 0.9) if wdrow.get("wikipedia") else None,
        "glottolog_code": val(gl_code, "wikidata", 0.9) if gl_code else None,
        "resource_level": None,  # filled below
        "data_source": None,     # filled below
        "provenance": {"wikidata": wdrow, "glottolog": gl, "geo": geo.get(iso3) if geo else None}
    }
