# 🌍 Omnilingual Language Finder

### *Find the Right Language Code for 1,600+ Languages in Seconds*

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Built for [Meta's Omnilingual ASR](https://github.com/facebookresearch/omnilingual-asr)**

[🚀 Quick Start](#quick-start) • [📚 Documentation](#documentation) • [🎯 Examples](#examples) • [🤝 Contributing](#contributing)

</div>

---

## 💡 Why This Exists

Meta's groundbreaking [Omnilingual ASR](https://github.com/facebookresearch/omnilingual-asr) supports **1,600+ languages**—more than any other speech recognition system. But there's a problem:

> **How do you find YOUR language code?**

```python
# ❌ The hard way (searching through docs)
# Is my language "bho_Deva" or "bhj_Deva"? 
# Does it support Chittagonian? Garhwali? Bhili?

# ✅ The easy way (with Language Finder)
from finder import LanguageFinder

finder = LanguageFinder()
code = finder.find("Bhojpuri")  # Returns: "bho_Deva"

languages = finder.search(region="Maharashtra")
# [Marathi, Hindi, Urdu, ...]
```

**This library is the missing link** between Meta's incredible technology and the communities who need it most.

---

## 🎯 Features

### 🔍 **Intuitive Search**
```python
# By name (English or native)
finder.find("हिन्दी")  # Works with native scripts!

# By region
finder.search(region="Bihar", country="IN")

# By script
finder.search(script="Devanagari", min_speakers=1_000_000)

# Complex filters
finder.search(
    country="IN",
    script="Devanagari",
    resource_level="high",
    min_speakers=10_000_000
)
```

### 📊 **Rich Metadata**
Every language includes:
- ✅ English & native names
- ✅ Speaker counts & demographics
- ✅ Geographic distribution (countries, regions)
- ✅ Script information
- ✅ Language family
- ✅ Resource level (high/medium/low)
- ✅ Related languages
- ✅ Wikipedia & Glottolog links

### 🗺️ **Geographic Browsing**
```python
# Browse by region
south_asia = finder.browse_region("South Asia")
# Returns: {India: [...], Pakistan: [...], Nepal: [...]}

# Find alternatives for fallback
alternatives = finder.get_alternatives("bho_Deva")
# Returns high-resource languages with same script, nearby
```

### 🎨 **Beautiful CLI**
```bash
# Search from terminal
omnilingual-finder search --region "Maharashtra" --script Devanagari

# Get detailed info
omnilingual-finder info hin_Deva

# Browse regions
omnilingual-finder browse "South Asia"

# Statistics
omnilingual-finder stats
```

---

## 🚀 Quick Start

### Installation

```bash
# From source (recommended for now)
git clone https://github.com/Baavro/omnilingual-finder.git
cd omnilingual-finder

# Build language database
python -m scripts.build_incremental --scripts Deva,Latn,Arab
python -m scripts.build_index

# Install package
pip install -e .
```

### Python API

```python
from finder import LanguageFinder

# Initialize (auto-discovers data)
finder = LanguageFinder()

# Find a language
hindi = finder.find("Hindi")
print(f"Code: {hindi.code}")
print(f"Speakers: {hindi.speaker_count:,}")
print(f"Regions: {', '.join(hindi.regions)}")

# Search with filters
results = finder.search(
    region="Maharashtra",
    min_speakers=1_000_000,
    sort_by="speakers",
    limit=5
)

for lang in results:
    print(f"{lang.english_name}: {lang.code}")
```

### Command Line

```bash
# Find Hindi
omnilingual-finder search --name Hindi

# Languages in Maharashtra with 1M+ speakers
omnilingual-finder search --region Maharashtra --min-speakers 1000000

# Get detailed information
omnilingual-finder info mar_Deva

# Browse South Asian languages
omnilingual-finder browse "South Asia"

# Export high-resource languages
omnilingual-finder export high_resource.json --filter high-resource
```

---

## 📚 Documentation

### Core API

#### `LanguageFinder(data_path=None)`
Main interface for language discovery.

#### `find(query: str) -> Language`
Find a single language by name, code, or ISO 639-3.

```python
hindi = finder.find("Hindi")
bhojpuri = finder.find("bho_Deva")
```

#### `search(**filters) -> List[Language]`
Powerful multi-criteria search.

**Filters:**
- `name`: Language name (fuzzy matching)
- `country`: ISO2 code or country name
- `region`: Geographic region/state
- `script`: Script code or name
- `family`: Language family
- `resource_level`: high, medium, low, zero-shot
- `min_speakers`, `max_speakers`: Speaker count range
- `limit`: Max results
- `sort_by`: speakers, name, resource, family

```python
# All Devanagari languages in India
results = finder.search(country="IN", script="Devanagari")

# High-resource languages
results = finder.search(resource_level="high", min_speakers=10_000_000)

# Regional search
results = finder.search(region="Tamil Nadu", sort_by="speakers")
```

#### `browse_region(region: str) -> Dict[str, List[Language]]`
Browse languages by geographic hierarchy.

```python
south_asia = finder.browse_region("South Asia")
# Returns: {India: [...], Pakistan: [...], Nepal: [...]}
```

#### `get_related(code: str) -> List[Language]`
Get linguistically related languages.

```python
related = finder.get_related("hin_Deva")
# Returns: [Bhojpuri, Awadhi, Maithili, ...]
```

#### `get_alternatives(code: str) -> List[Language]`
Get high-resource alternatives (for fallback).

```python
alternatives = finder.get_alternatives("bho_Deva")
# Returns: [Hindi, Maithili] (same script, nearby, high-resource)
```

### Language Object

```python
class Language:
    code: str                    # "hin_Deva"
    iso_639_3: str              # "hin"
    script_code: str            # "Deva"
    
    english_name: str           # "Hindi"
    native_name: str            # "हिन्दी"
    
    countries: List[str]        # ["IN", "NP", "FJ"]
    regions: List[str]          # ["Uttar Pradesh", "Bihar", ...]
    coordinates: Dict           # {lat, lon}
    
    language_family: str        # "Indo-Aryan"
    script_name: str            # "Devanagari"
    writing_direction: str      # "ltr"
    
    speaker_count: int          # 341000000
    resource_level: str         # "high"
    data_source: str           # "both"
    
    related_languages: List[str]
    wikipedia_code: str
    glottolog_code: str
```

---

## 🎯 Examples

### Example 1: Building a Voice Assistant

```python
finder = LanguageFinder()

# User selects their state
user_state = "Karnataka"
languages = finder.search(region=user_state, sort_by="speakers")

print(f"Available languages: {', '.join(l.english_name for l in languages)}")

# User picks Kannada
chosen = finder.find("Kannada")
print(f"ASR Code: {chosen.code}")  # kan_Knda

# Set up fallbacks
alternatives = finder.get_alternatives(chosen.code)
print(f"Fallbacks: {', '.join(a.code for a in alternatives)}")
```

### Example 2: Research Dataset

```python
# Get all Indo-Aryan languages for dialectology study
indo_aryan = finder.search(
    family="Indo-Aryan",
    country="IN",
    min_speakers=500_000
)

# Group by script
by_script = {}
for lang in indo_aryan:
    script = lang.script_name
    by_script.setdefault(script, []).append(lang)

# Export for ASR experiments
finder.export_json(
    "indo_aryan_languages.json",
    filter_fn=lambda l: l.language_family == "Indo-Aryan"
)
```

### Example 3: Multilingual App

```python
# Phase 1: High-resource languages
tier1 = finder.search(resource_level="high")
print(f"Launch with {len(tier1)} languages")

# Phase 2: Regional expansion
for country in ["IN", "ID", "NG", "BR"]:
    langs = finder.search(country=country, min_speakers=1_000_000)
    print(f"{country}: Add {len(langs)} languages")

# Total coverage
total = finder.statistics()
print(f"Total: {total['total_languages']} languages, {total['total_speakers']:,} speakers")
```

### More Examples

See [`examples/usage_examples.py`](examples/usage_examples.py) for 13 comprehensive examples covering:
- Simple searches
- Complex filtering
- Regional browsing
- Language families
- Real-world use cases (voice assistants, research, apps)

---

## 📊 Coverage Statistics

| Region | Languages | Scripts | Top Families |
|--------|-----------|---------|--------------|
| 🇮🇳 South Asia | 350+ | 10+ | Indo-Aryan, Dravidian |
| 🌍 Sub-Saharan Africa | 500+ | 5+ | Niger-Congo, Afroasiatic |
| 🌏 Southeast Asia | 200+ | 15+ | Austronesian, Sino-Tibetan |
| 📍 Americas | 150+ | 3+ | Uto-Aztecan, Mayan |
| 🌐 Other | 400+ | 20+ | Various |

**Total: 1,600+ languages • 200+ countries • 50+ scripts**

---

## 🏗️ How It Works

### Data Pipeline

```
1. Source Data
   ├─ ISO 639-3 (language codes, names)
   ├─ Wikidata (speakers, native names, geo)
   ├─ Glottolog (families, coordinates)
   └─ Community overrides

2. Incremental Builder (scripts/build_incremental.py)
   ├─ Fetches metadata in batches
   ├─ Merges from multiple sources
   ├─ Handles failures gracefully
   └─ Outputs: data/languages.json

3. Index Builder (scripts/build_index.py)
   ├─ Creates fast lookup indices
   ├─ Normalizes for fuzzy matching
   └─ Outputs: data/finder_index.json

4. Finder (finder/core.py)
   ├─ Loads languages + indices
   ├─ Rich Language objects
   └─ Intuitive search API
```

### Key Design Decisions

- **Zero external dependencies** (stdlib only)
- **Offline-first**: No API calls after build
- **Fuzzy matching**: Works with partial names, typos
- **Multi-source**: Combines authoritative data sources
- **Community-driven**: Easy to add overrides

---

## 🤝 Contributing

We believe language metadata should be **by the community, for the community**.

### How to Contribute

1. **Improve Language Data**
   - Native speaker? Add/fix native names
   - Know regional usage? Update regions
   - See mistakes? Open an issue

2. **Add Languages**
   - Missing a variant? Add to `sources/overrides/`
   - New script support? Update extractors

3. **Enhance Features**
   - Better search algorithms
   - New indices
   - Performance improvements

4. **Documentation**
   - Add examples
   - Improve guides
   - Translate README

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Development Setup

```bash
# Clone repo
git clone https://github.com/Baavro/omnilingual-finder.git
cd omnilingual-finder

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Format code
black finder/ scripts/

# Build data
python -m scripts.build_incremental --scripts "*"  # All scripts
python -m scripts.build_index
```

---

## 🎓 Citation

If you use this tool in research:

```bibtex
@software{omnilingual_finder,
  title={Omnilingual Language Finder: Geographic Discovery for Multilingual Speech Recognition},
  author={Your Name},
  year={2025},
  url={https://github.com/Baavro/omnilingual-finder}
}
```

Please also cite the Omnilingual ASR paper:
```bibtex
@article{omnilingual_asr_2025,
  title={Omnilingual ASR: Scaling Automatic Speech Recognition to 1,600+ Languages},
  author={Meta AI Research},
  year={2025},
  journal={arXiv}
}
```

---

## 📜 License

MIT License - See [LICENSE](LICENSE)

### Data Sources

This project combines data from:
- [ISO 639-3](https://iso639-3.sil.org/) - SIL International
- [Wikidata](https://www.wikidata.org/) - Wikimedia Foundation
- [Glottolog](https://glottolog.org/) - Max Planck Institute

All data sources are properly attributed in the metadata.

---

## 🙏 Acknowledgments

- **Meta AI Research** for building Omnilingual ASR
- **SIL International** for maintaining ISO 639-3
- **Glottolog** for linguistic classifications
- **Wikidata** contributors for crowdsourced data
- **Language communities** who shared their knowledge

---

## 🗺️ Roadmap

- [x] Core metadata extraction (1,600+ languages)
- [x] Python SDK with rich API
- [x] Command-line interface
- [ ] Interactive web map 🚧
- [ ] Browser extension
- [ ] Mobile app for field researchers
- [ ] Audio samples for each language
- [ ] Community contribution portal
- [ ] Integration examples with ASR frameworks

---

<div align="center">

**🌍 Every Language Deserves Voice Technology 🎤**

Made with ❤️ for the world's 7,000+ language communities

[⭐ Star this repo](https://github.com/Baavro/omnilingual-finder) • [🐛 Report Bug](https://github.com/Baavro/omnilingual-finder/issues) • [💡 Request Feature](https://github.com/Baavro/omnilingual-finder/issues)

</div>