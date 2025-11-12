"""
Omnilingual Language Finder - Usage Examples
Comprehensive guide showing all features
"""
from finder.core import LanguageFinder

def example_1_simple_search():
    """Example 1: Simple name search"""
    print("=" * 60)
    print("Example 1: Find a language by name")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    # Find Hindi
    hindi = finder.find("Hindi")
    print(f"\n✅ Found: {hindi}")
    print(f"   Code: {hindi.code}")
    print(f"   Speakers: {hindi.speaker_count:,}")
    print(f"   Script: {hindi.script_name}")
    print(f"   Countries: {', '.join(hindi.countries)}")
    
    # Also works with partial names
    bhoj = finder.find("Bhoj")  # Finds Bhojpuri
    print(f"\n✅ Fuzzy match: {bhoj}")


def example_2_regional_search():
    """Example 2: Find all languages in a region"""
    print("\n" + "=" * 60)
    print("Example 2: Languages in Maharashtra")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    languages = finder.search(region="Maharashtra", limit=5)
    
    print(f"\n✅ Found {len(languages)} languages in Maharashtra:")
    for lang in languages:
        speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "Unknown"
        print(f"\n   • {lang.english_name} ({lang.code})")
        print(f"     Native: {lang.native_name}")
        print(f"     Speakers: {speakers}")
        print(f"     Resource: {lang.resource_level}")


def example_3_complex_filter():
    """Example 3: Complex multi-criteria search"""
    print("\n" + "=" * 60)
    print("Example 3: High-resource Devanagari languages in India")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    results = finder.search(
        country="IN",
        script="Devanagari",
        resource_level="high",
        min_speakers=10_000_000,
        sort_by="speakers"
    )
    
    print(f"\n✅ Found {len(results)} languages matching all criteria:")
    for lang in results:
        print(f"\n   {lang.english_name:20} {lang.speaker_count:>15,} speakers")
        print(f"   {'':20} Regions: {', '.join(lang.regions[:3])}")


def example_4_script_comparison():
    """Example 4: Compare languages by script"""
    print("\n" + "=" * 60)
    print("Example 4: Script comparison in India")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    scripts = ["Devanagari", "Bengali", "Telugu", "Tamil"]
    
    for script in scripts:
        langs = finder.search(country="IN", script=script, limit=3)
        print(f"\n📜 {script} script ({len(langs)} major languages):")
        for lang in langs:
            speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "?"
            print(f"   • {lang.english_name:20} {speakers:>15} speakers")


def example_5_language_families():
    """Example 5: Explore language families"""
    print("\n" + "=" * 60)
    print("Example 5: Indo-Aryan vs Dravidian languages")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    families = ["Indo-Aryan", "Dravidian"]
    
    for family in families:
        langs = finder.search(
            family=family,
            country="IN",
            min_speakers=1_000_000,
            sort_by="speakers",
            limit=5
        )
        
        total_speakers = sum(l.speaker_count for l in langs if l.speaker_count)
        
        print(f"\n🌳 {family} family ({len(langs)} major languages in India):")
        print(f"   Total speakers: {total_speakers:,}")
        
        for lang in langs:
            speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "?"
            print(f"   • {lang.english_name:20} {speakers:>15}")


def example_6_related_languages():
    """Example 6: Find related languages"""
    print("\n" + "=" * 60)
    print("Example 6: Languages related to Hindi")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    hindi = finder.find("Hindi")
    related = finder.get_related(hindi.code)
    
    print(f"\n🔗 Languages related to {hindi.english_name}:")
    print(f"   (Same family: {hindi.language_family}, Same script: {hindi.script_name})")
    
    for lang in related:
        speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "Unknown"
        print(f"\n   • {lang.english_name} ({lang.code})")
        print(f"     Speakers: {speakers}")
        print(f"     Regions: {', '.join(lang.regions[:2])}")


def example_7_alternatives():
    """Example 7: Find alternatives for fallback"""
    print("\n" + "=" * 60)
    print("Example 7: Find high-resource alternatives to Bhojpuri")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    bhojpuri = finder.find("Bhojpuri")
    alternatives = finder.get_alternatives(bhojpuri.code)
    
    print(f"\n💡 If {bhojpuri.english_name} isn't working well, try:")
    print(f"   (Same script, nearby regions, better resources)")
    
    for alt in alternatives:
        print(f"\n   ✓ {alt.english_name} ({alt.code})")
        print(f"     Resource: {alt.resource_level}")
        print(f"     Speakers: {alt.speaker_count:,}" if alt.speaker_count else "     Speakers: Unknown")
        print(f"     Regions: {', '.join(alt.regions[:2])}")


def example_8_browse_hierarchy():
    """Example 8: Browse by geographic hierarchy"""
    print("\n" + "=" * 60)
    print("Example 8: Browse South Asian languages")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    regions = finder.browse_region("South Asia")
    
    print("\n🗺️  South Asian Languages by Country:\n")
    
    for country, langs in list(regions.items())[:3]:  # Show first 3 countries
        # Get top 3 languages by speakers
        top_langs = sorted(
            langs,
            key=lambda x: -x.speaker_count if x.speaker_count else 0
        )[:3]
        
        total = sum(l.speaker_count for l in langs if l.speaker_count)
        
        print(f"📍 {country} ({len(langs)} languages, {total:,} total speakers)")
        for lang in top_langs:
            speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "?"
            print(f"   • {lang.english_name:20} {speakers:>15} speakers  [{lang.code}]")
        print()


def example_9_statistics():
    """Example 9: Get insights with statistics"""
    print("\n" + "=" * 60)
    print("Example 9: Statistical insights")
    print("=" * 60)
    
    finder = LanguageFinder()
    stats = finder.statistics()
    
    print(f"\n📊 Dataset Overview:")
    print(f"   Total languages:  {stats['total_languages']:,}")
    print(f"   Total scripts:    {stats['total_scripts']}")
    print(f"   Total families:   {stats['total_families']}")
    print(f"   Total speakers:   {stats['total_speakers']:,}")
    
    print(f"\n📈 Top 5 Scripts:")
    for item in stats['by_script'][:5]:
        print(f"   {item['value']:15} {item['count']:4} languages")
    
    print(f"\n🌍 Top 5 Countries:")
    for item in stats['by_country'][:5]:
        print(f"   {item['country']:5} {item['count']:4} languages")


def example_10_export():
    """Example 10: Export filtered datasets"""
    print("\n" + "=" * 60)
    print("Example 10: Export custom datasets")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    # Export only high-resource languages
    finder.export_json(
        "/tmp/high_resource_languages.json",
        filter_fn=lambda l: l.resource_level == "high"
    )
    print("\n✅ Exported high-resource languages")
    
    # Export endangered languages
    finder.export_json(
        "/tmp/endangered_languages.json",
        filter_fn=lambda l: l.is_endangered
    )
    print("✅ Exported endangered languages (<1M speakers)")
    
    # Export South Asian languages
    south_asian_codes = {"IN", "PK", "NP", "BD", "LK", "BT"}
    finder.export_json(
        "/tmp/south_asian_languages.json",
        filter_fn=lambda l: any(c in south_asian_codes for c in l.countries)
    )
    print("✅ Exported South Asian languages")


def example_11_use_case_voice_assistant():
    """Example 11: Real use case - Building a voice assistant"""
    print("\n" + "=" * 60)
    print("Example 11: Real-world use case - Voice Assistant")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    print("\n🎤 Building a voice assistant for Indian users:")
    print("   Step 1: User selects their state")
    
    user_state = "Karnataka"
    languages = finder.search(region=user_state, sort_by="speakers")
    
    print(f"\n   Step 2: Show available languages for {user_state}")
    print(f"   Available: {', '.join(l.english_name for l in languages[:5])}")
    
    # User picks Kannada
    chosen = finder.find("Kannada")
    print(f"\n   Step 3: User picks {chosen.english_name}")
    print(f"   ASR Code: {chosen.code}")
    print(f"   Resource Level: {chosen.resource_level}")
    
    # Get fallback options
    alternatives = finder.get_alternatives(chosen.code)
    print(f"\n   Step 4: Set up fallback languages:")
    for alt in alternatives[:2]:
        print(f"   Fallback: {alt.english_name} ({alt.code})")
    
    print("\n   ✅ Voice assistant configured!")


def example_12_use_case_research():
    """Example 12: Real use case - Research dataset"""
    print("\n" + "=" * 60)
    print("Example 12: Research use case - Dialectology study")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    print("\n🔬 Research: Indo-Aryan dialect continuum")
    print("   Research question: How do Hindi dialects vary?")
    
    # Get Hindi and related languages
    hindi = finder.find("Hindi")
    related = finder.search(
        family="Indo-Aryan",
        country="IN",
        script="Devanagari",
        sort_by="speakers"
    )
    
    print(f"\n   Found {len(related)} Indo-Aryan Devanagari languages in India:")
    
    # Group by region
    by_region = {}
    for lang in related:
        for region in lang.regions[:1]:  # Take first region
            if region not in by_region:
                by_region[region] = []
            by_region[region].append(lang)
    
    print(f"\n   Geographic distribution:")
    for region in list(by_region.keys())[:5]:
        langs = by_region[region]
        print(f"   {region:20} {len(langs)} languages")
        for lang in langs[:2]:
            print(f"      • {lang.english_name} ({lang.code})")
    
    print("\n   ✅ Dataset ready for ASR experiments!")


def example_13_use_case_app():
    """Example 13: Real use case - Multilingual app"""
    print("\n" + "=" * 60)
    print("Example 13: App use case - Add 1,600 languages to your product")
    print("=" * 60)
    
    finder = LanguageFinder()
    
    print("\n🚀 Adding speech recognition to a productivity app:")
    
    # Step 1: Support high-resource languages first
    tier1 = finder.search(resource_level="high", limit=20)
    print(f"\n   Phase 1: Launch with {len(tier1)} high-resource languages")
    print(f"   Coverage: {sum(l.speaker_count for l in tier1 if l.speaker_count):,} speakers")
    
    # Step 2: Add regional languages
    print("\n   Phase 2: Add regional languages by market:")
    markets = ["India", "Indonesia", "Nigeria"]
    for market in markets:
        langs = finder.search(country=market[:2].upper(), min_speakers=1_000_000)
        print(f"   {market:15} {len(langs):3} languages")
    
    # Step 3: Long tail
    low_resource = finder.search(resource_level="low")
    print(f"\n   Phase 3: Long-tail support")
    print(f"   Add {len(low_resource)} low-resource languages")
    print(f"   Total: {len(tier1) + len(low_resource)} languages 🎉")


def run_all_examples():
    """Run all examples"""
    examples = [
        example_1_simple_search,
        example_2_regional_search,
        example_3_complex_filter,
        example_4_script_comparison,
        example_5_language_families,
        example_6_related_languages,
        example_7_alternatives,
        example_8_browse_hierarchy,
        example_9_statistics,
        example_10_export,
        example_11_use_case_voice_assistant,
        example_12_use_case_research,
        example_13_use_case_app,
    ]
    
    for ex in examples:
        ex()
        input("\n[Press Enter for next example...]")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run specific example
        example_num = int(sys.argv[1])
        examples = [
            example_1_simple_search, example_2_regional_search,
            example_3_complex_filter, example_4_script_comparison,
            example_5_language_families, example_6_related_languages,
            example_7_alternatives, example_8_browse_hierarchy,
            example_9_statistics, example_10_export,
            example_11_use_case_voice_assistant, example_12_use_case_research,
            example_13_use_case_app,
        ]
        if 1 <= example_num <= len(examples):
            examples[example_num - 1]()
        else:
            print(f"Example {example_num} not found. Choose 1-{len(examples)}")
    else:
        # Run all examples
        run_all_examples()