"""
Omnilingual Language Finder - Production Core
Rich, intuitive API for discovering ASR language codes
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Callable
from pathlib import Path
import json
import unicodedata
import re


def _norm(s: str) -> str:
    """Normalize string for fuzzy matching"""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s.lower()).strip()


@dataclass
class Language:
    """
    Rich language object with all metadata.
    
    Designed to be:
    - Intuitive: dot notation for all properties
    - Complete: all metadata in one place
    - Printable: nice __repr__ for debugging
    """
    code: str
    iso_639_3: str
    script_code: str
    
    # Names
    english_name: str
    native_name: Optional[str] = None
    autonym: Optional[str] = None
    
    # Geographic
    countries: List[str] = field(default_factory=list)  # ISO2 codes
    country_names: List[str] = field(default_factory=list)  # Human-readable
    regions: List[str] = field(default_factory=list)  # Sub-national
    coordinates: Optional[Dict[str, float]] = None  # {lat, lon}
    
    # Linguistic
    language_family: Optional[str] = None
    script_name: str = ""
    writing_direction: str = "ltr"
    
    # Demographics
    speaker_count: Optional[int] = None
    speaker_count_source: Optional[str] = None
    
    # ASR Metadata
    resource_level: str = "low"  # high/medium/low/zero-shot
    data_source: str = "community"  # public/community/both
    
    # Related
    related_languages: List[str] = field(default_factory=list)
    
    # External IDs
    wikipedia_code: Optional[str] = None
    glottolog_code: Optional[str] = None
    
    # Internal
    _raw: Dict = field(default_factory=dict, repr=False)
    
    def __repr__(self):
        speakers = f"{self.speaker_count:,}" if self.speaker_count else "?"
        return f"Language({self.code}: {self.english_name}, {speakers} speakers, {self.resource_level})"
    
    def __str__(self):
        return f"{self.english_name} ({self.code})"
    
    @property
    def display_name(self) -> str:
        """Best display name (native if available, else English)"""
        return self.native_name or self.autonym or self.english_name
    
    @property
    def primary_country(self) -> Optional[str]:
        """First/primary country where spoken"""
        return self.countries[0] if self.countries else None
    
    @property
    def is_high_resource(self) -> bool:
        return self.resource_level == "high"
    
    @property
    def is_endangered(self) -> bool:
        """Heuristic: <1M speakers = potentially endangered"""
        return self.speaker_count is not None and self.speaker_count < 1_000_000
    
    def to_dict(self) -> Dict:
        """Serialize to dict (for JSON export)"""
        return {
            "code": self.code,
            "iso_639_3": self.iso_639_3,
            "script_code": self.script_code,
            "english_name": self.english_name,
            "native_name": self.native_name,
            "autonym": self.autonym,
            "countries": self.countries,
            "country_names": self.country_names,
            "regions": self.regions,
            "coordinates": self.coordinates,
            "language_family": self.language_family,
            "script_name": self.script_name,
            "writing_direction": self.writing_direction,
            "speaker_count": self.speaker_count,
            "resource_level": self.resource_level,
            "data_source": self.data_source,
            "related_languages": self.related_languages,
            "wikipedia_code": self.wikipedia_code,
            "glottolog_code": self.glottolog_code,
        }


class LanguageFinder:
    """
    Intuitive, powerful language discovery engine.
    
    Usage:
        finder = LanguageFinder()
        
        # Simple searches
        hindi = finder.find("Hindi")
        maharashtra = finder.search(region="Maharashtra")
        
        # Complex filtering
        results = finder.search(
            country="IN",
            script="Devanagari", 
            min_speakers=10_000_000,
            resource_level="high"
        )
        
        # Browse by region
        south_asia = finder.browse_region("South Asia")
    """
    
    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize finder.
        
        Args:
            data_path: Path to languages.json. Auto-discovers if None.
        """
        self.data_path = self._discover_data_path(data_path)
        self._languages: Dict[str, Language] = {}
        self._indices: Dict[str, Dict] = {}
        
        self._load_data()
        self._build_indices()
        self._build_regional_hierarchy()
    
    def _discover_data_path(self, explicit: Optional[Path]) -> Path:
        """Smart path discovery"""
        if explicit and explicit.exists():
            return explicit
        
        # Try common locations
        candidates = [
            Path("data/languages.json"),
            Path("../data/languages.json"),
            Path(__file__).parent.parent / "data" / "languages.json",
        ]
        
        for p in candidates:
            if p.exists():
                return p
        
        raise FileNotFoundError(
            "Cannot find languages.json. Run: python -m scripts.build_incremental"
        )
    
    def _load_data(self):
        """Load and parse language data into rich Language objects"""
        raw = json.loads(self.data_path.read_text())
        
        for code, data in raw.items():
            # Extract values from {value, source, confidence} structure
            def _v(field, fallback=None):
                val = data.get(field)
                if isinstance(val, dict):
                    return val.get("value", fallback)
                return val or fallback
            
            # Parse coordinates
            coords = data.get("coordinates")
            if coords and isinstance(coords, dict):
                if coords.get("lat") is not None:
                    coords = {"lat": coords["lat"], "lon": coords["lon"]}
                else:
                    coords = None
            
            lang = Language(
                code=code,
                iso_639_3=data.get("iso_639_3", ""),
                script_code=data.get("script_code", ""),
                english_name=_v("english_name", code),
                native_name=_v("autonym"),
                autonym=_v("autonym"),
                countries=data.get("primary_countries", []),
                country_names=data.get("provenance", {}).get("geo", {}).get("countries_labels", []),
                regions=data.get("regions", []),
                coordinates=coords,
                language_family=_v("language_family"),
                script_name=_v("script_name", data.get("script_code", "")),
                writing_direction=_v("writing_direction", "ltr"),
                speaker_count=_v("speaker_count"),
                speaker_count_source=_v("speaker_count") and "wikidata",
                resource_level=_v("resource_level", "low"),
                data_source=_v("data_source", "community"),
                related_languages=data.get("related_languages", []),
                wikipedia_code=_v("wikipedia_code"),
                glottolog_code=_v("glottolog_code"),
                _raw=data
            )
            
            self._languages[code] = lang
    
    def _build_indices(self):
        """Build fast lookup indices"""
        self._indices = {
            "by_name": {},        # english_name -> [codes]
            "by_native": {},      # native_name -> [codes]
            "by_iso3": {},        # iso_639_3 -> [codes]
            "by_script": {},      # script_code -> [codes]
            "by_script_name": {}, # script_name -> [codes]
            "by_country": {},     # country ISO2 -> [codes]
            "by_region": {},      # region name -> [codes]
            "by_family": {},      # language_family -> [codes]
            "by_resource": {},    # resource_level -> [codes]
        }
        
        for code, lang in self._languages.items():
            # Names
            self._index_add("by_name", _norm(lang.english_name), code)
            if lang.native_name:
                self._index_add("by_native", _norm(lang.native_name), code)
            if lang.autonym and lang.autonym != lang.native_name:
                self._index_add("by_native", _norm(lang.autonym), code)
            
            # IDs
            self._index_add("by_iso3", lang.iso_639_3, code)
            
            # Scripts
            self._index_add("by_script", lang.script_code, code)
            self._index_add("by_script_name", _norm(lang.script_name), code)
            
            # Geography
            for country in lang.countries:
                self._index_add("by_country", country, code)
                self._index_add("by_country", country.lower(), code)
            
            for region in lang.regions:
                self._index_add("by_region", _norm(region), code)
            
            # Linguistic
            if lang.language_family:
                self._index_add("by_family", _norm(lang.language_family), code)
            
            # Metadata
            self._index_add("by_resource", lang.resource_level, code)
    
    def _index_add(self, index_name: str, key: str, code: str):
        """Helper to add to index"""
        if not key:
            return
        if key not in self._indices[index_name]:
            self._indices[index_name][key] = []
        if code not in self._indices[index_name][key]:
            self._indices[index_name][key].append(code)
    
    def _build_regional_hierarchy(self):
        """Build geographic hierarchy for browse_region()"""
        self._regions = {
            "South Asia": {
                "India": {
                    "North India": ["Delhi", "Haryana", "Punjab", "Uttarakhand", "Himachal Pradesh"],
                    "Hindi Belt": ["Uttar Pradesh", "Bihar", "Madhya Pradesh", "Rajasthan", "Chhattisgarh"],
                    "East India": ["West Bengal", "Odisha", "Jharkhand", "Assam", "Tripura"],
                    "West India": ["Maharashtra", "Gujarat", "Goa"],
                    "South India": ["Tamil Nadu", "Karnataka", "Kerala", "Andhra Pradesh", "Telangana"],
                },
                "Pakistan": ["Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan"],
                "Bangladesh": [],
                "Nepal": [],
                "Sri Lanka": [],
                "Bhutan": [],
            },
            "Southeast Asia": {
                "Indonesia": [],
                "Philippines": [],
                "Thailand": [],
                "Vietnam": [],
                "Myanmar": [],
            },
            "East Asia": {
                "China": [],
                "Japan": [],
                "Korea": [],
            },
            "Africa": {
                "West Africa": [],
                "East Africa": [],
                "Southern Africa": [],
                "North Africa": [],
            },
            "Europe": {},
            "Americas": {},
        }
    
    # ==================== Public API ====================
    
    def find(self, query: str) -> Optional[Language]:
        """
        Find a single language by name, code, or ISO.
        
        Args:
            query: Language name, code, or ISO 639-3
        
        Returns:
            Best matching Language or None
        
        Example:
            >>> finder.find("Hindi")
            Language(hin_Deva: Hindi, 341,000,000 speakers)
        """
        results = self.search(name=query, limit=1)
        return results[0] if results else None
    
    def get(self, code: str) -> Optional[Language]:
        """
        Get language by exact code.
        
        Args:
            code: Full language code (e.g., "hin_Deva")
        
        Returns:
            Language object or None
        """
        return self._languages.get(code)
    
    def search(
        self,
        name: Optional[str] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
        script: Optional[str] = None,
        family: Optional[str] = None,
        resource_level: Optional[str] = None,
        data_source: Optional[str] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        limit: Optional[int] = None,
        sort_by: str = "speakers",  # speakers, name, resource
    ) -> List[Language]:
        """
        Powerful multi-criteria search.
        
        Args:
            name: Language name (English or native, fuzzy matching)
            country: ISO2 country code or name (e.g., "IN" or "India")
            region: Geographic region (e.g., "Maharashtra", "Punjab")
            script: Script code or name (e.g., "Deva" or "Devanagari")
            family: Language family (e.g., "Indo-Aryan", "Dravidian")
            resource_level: "high", "medium", "low", "zero-shot"
            data_source: "public", "community", "both"
            min_speakers: Minimum speaker count
            max_speakers: Maximum speaker count
            limit: Max results to return
            sort_by: "speakers", "name", "resource", "family"
        
        Returns:
            List of matching Language objects
        
        Examples:
            # Simple name search
            >>> finder.search(name="Hindi")
            
            # Regional search
            >>> finder.search(country="IN", region="Maharashtra")
            
            # Complex filter
            >>> finder.search(
                    script="Devanagari",
                    country="IN",
                    min_speakers=1_000_000,
                    resource_level="high"
                )
        """
        # Start with all languages
        candidates = set(self._languages.keys())
        
        # Apply filters progressively (AND logic)
        
        if name:
            name_matches = self._search_by_name(name)
            if name_matches:
                candidates &= name_matches
            else:
                return []  # No name matches = no results
        
        if country:
            country_codes = self._search_by_country(country)
            if country_codes:
                candidates &= country_codes
        
        if region:
            region_codes = self._search_by_region(region)
            if region_codes:
                candidates &= region_codes
        
        if script:
            script_codes = self._search_by_script(script)
            if script_codes:
                candidates &= script_codes
        
        if family:
            fam_norm = _norm(family)
            family_codes = set(self._indices["by_family"].get(fam_norm, []))
            if family_codes:
                candidates &= family_codes
        
        if resource_level:
            res_codes = set(self._indices["by_resource"].get(resource_level, []))
            if res_codes:
                candidates &= res_codes
        
        # Convert to Language objects and apply numeric filters
        results = []
        for code in candidates:
            lang = self._languages[code]
            
            if data_source and lang.data_source != data_source:
                continue
            
            if min_speakers is not None:
                if lang.speaker_count is None or lang.speaker_count < min_speakers:
                    continue
            
            if max_speakers is not None:
                if lang.speaker_count is not None and lang.speaker_count > max_speakers:
                    continue
            
            results.append(lang)
        
        # Sort
        results = self._sort_results(results, sort_by)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def _search_by_name(self, query: str) -> Set[str]:
        """Search by English or native name with fuzzy matching"""
        q_norm = _norm(query)
        matches = set()
        
        # Exact matches
        matches.update(self._indices["by_name"].get(q_norm, []))
        matches.update(self._indices["by_native"].get(q_norm, []))
        
        # Fuzzy: check if query is substring of any name
        if not matches:
            for name, codes in self._indices["by_name"].items():
                if q_norm in name or name in q_norm:
                    matches.update(codes)
            
            for name, codes in self._indices["by_native"].items():
                if q_norm in name or name in q_norm:
                    matches.update(codes)
        
        # ISO3 fallback
        if not matches and len(query) == 3:
            matches.update(self._indices["by_iso3"].get(query.lower(), []))
        
        return matches
    
    def _search_by_country(self, query: str) -> Set[str]:
        """Search by country code or name"""
        matches = set()
        
        # Try as ISO2
        if len(query) == 2:
            matches.update(self._indices["by_country"].get(query.upper(), []))
            matches.update(self._indices["by_country"].get(query.lower(), []))
        
        # Try as country name (fuzzy)
        q_norm = _norm(query)
        for code in self._languages.values():
            for cname in code.country_names:
                if q_norm in _norm(cname) or _norm(cname) in q_norm:
                    matches.add(code.code)
        
        return matches
    
    def _search_by_region(self, query: str) -> Set[str]:
        """Search by region/state name"""
        q_norm = _norm(query)
        matches = set()
        
        # Exact
        matches.update(self._indices["by_region"].get(q_norm, []))
        
        # Fuzzy
        if not matches:
            for region, codes in self._indices["by_region"].items():
                if q_norm in region or region in q_norm:
                    matches.update(codes)
        
        return matches
    
    def _search_by_script(self, query: str) -> Set[str]:
        """Search by script code or name"""
        matches = set()
        
        # Try as code
        matches.update(self._indices["by_script"].get(query, []))
        
        # Try as name
        q_norm = _norm(query)
        matches.update(self._indices["by_script_name"].get(q_norm, []))
        
        # Common aliases
        aliases = {
            "devanagari": "Deva",
            "hindi": "Deva",
            "latin": "Latn",
            "roman": "Latn",
            "arabic": "Arab",
            "bengali": "Beng",
            "bangla": "Beng",
        }
        if q_norm in aliases:
            matches.update(self._indices["by_script"].get(aliases[q_norm], []))
        
        return matches
    
    def _sort_results(self, results: List[Language], sort_by: str) -> List[Language]:
        """Sort results by specified criteria"""
        if sort_by == "speakers":
            return sorted(
                results,
                key=lambda x: (-x.speaker_count if x.speaker_count else -1, x.english_name)
            )
        elif sort_by == "name":
            return sorted(results, key=lambda x: x.english_name)
        elif sort_by == "resource":
            order = {"high": 0, "medium": 1, "low": 2, "zero-shot": 3}
            return sorted(
                results,
                key=lambda x: (order.get(x.resource_level, 99), -x.speaker_count if x.speaker_count else 0)
            )
        elif sort_by == "family":
            return sorted(results, key=lambda x: (x.language_family or "ZZZ", x.english_name))
        else:
            return results
    
    def browse_region(self, region: str) -> Dict[str, List[Language]]:
        """
        Browse languages by geographic region with hierarchy.
        
        Args:
            region: Region name (e.g., "South Asia", "India", "Maharashtra")
        
        Returns:
            Dict mapping sub-regions to languages
        
        Example:
            >>> finder.browse_region("South Asia")
            {
                "India": [Language(...), ...],
                "Pakistan": [...],
                "Nepal": [...]
            }
        """
        result = {}
        
        # Try to find in hierarchy
        def search_hierarchy(tree, path=[]):
            if isinstance(tree, dict):
                for key, subtree in tree.items():
                    if _norm(region) in _norm(key):
                        # Found it! Return languages for this region
                        if isinstance(subtree, dict):
                            for subkey, subregions in subtree.items():
                                langs = self.search(region=subkey)
                                if langs:
                                    result[subkey] = langs
                        else:
                            result[key] = self.search(region=key)
                        return True
                    if search_hierarchy(subtree, path + [key]):
                        return True
            return False
        
        search_hierarchy(self._regions)
        
        # Fallback: direct region search
        if not result:
            langs = self.search(region=region)
            if langs:
                result[region] = langs
        
        return result
    
    def get_related(self, code: str, limit: int = 5) -> List[Language]:
        """Get related languages"""
        lang = self.get(code)
        if not lang:
            return []
        
        related_codes = lang.related_languages[:limit]
        return [self._languages[c] for c in related_codes if c in self._languages]
    
    def get_alternatives(self, code: str, limit: int = 5) -> List[Language]:
        """
        Get alternative languages (same script, nearby, high-resource).
        Useful for fallbacks.
        """
        lang = self.get(code)
        if not lang:
            return []
        
        alternatives = self.search(
            script=lang.script_code,
            resource_level="high",
            sort_by="speakers"
        )
        
        # Filter to same countries
        alternatives = [
            a for a in alternatives
            if set(a.countries) & set(lang.countries) and a.code != code
        ]
        
        return alternatives[:limit]
    
    def statistics(self) -> Dict:
        """Get overall statistics"""
        total_speakers = sum(
            lang.speaker_count for lang in self._languages.values()
            if lang.speaker_count
        )
        
        return {
            "total_languages": len(self._languages),
            "total_scripts": len(set(lang.script_code for lang in self._languages.values())),
            "total_families": len(set(lang.language_family for lang in self._languages.values() if lang.language_family)),
            "total_countries": len(set(c for lang in self._languages.values() for c in lang.countries)),
            "total_speakers": total_speakers,
            "by_resource_level": self._count_by("resource_level"),
            "by_script": self._count_by("script_code", top=10),
            "by_family": self._count_by("language_family", top=10),
            "by_country": self._count_by_country(top=10),
        }
    
    def _count_by(self, attr: str, top: int = None) -> List[Dict]:
        """Helper for statistics"""
        counts = {}
        for lang in self._languages.values():
            val = getattr(lang, attr, None)
            if val:
                counts[val] = counts.get(val, 0) + 1
        
        items = [{"value": k, "count": v} for k, v in counts.items()]
        items.sort(key=lambda x: -x["count"])
        
        return items[:top] if top else items
    
    def _count_by_country(self, top: int = None) -> List[Dict]:
        """Count languages by country"""
        counts = {}
        for lang in self._languages.values():
            for country in lang.countries:
                counts[country] = counts.get(country, 0) + 1
        
        items = [{"country": k, "count": v} for k, v in counts.items()]
        items.sort(key=lambda x: -x["count"])
        
        return items[:top] if top else items
    
    def export_json(
        self,
        filepath: str,
        filter_fn: Optional[Callable[[Language], bool]] = None
    ):
        """
        Export languages to JSON.
        
        Args:
            filepath: Output path
            filter_fn: Optional filter function
        
        Example:
            # Export only high-resource languages
            finder.export_json(
                "high_resource.json",
                filter_fn=lambda l: l.resource_level == "high"
            )
        """
        languages = self._languages.values()
        if filter_fn:
            languages = [l for l in languages if filter_fn(l)]
        
        data = {lang.code: lang.to_dict() for lang in languages}
        
        Path(filepath).write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
        )