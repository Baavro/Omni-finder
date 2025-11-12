#!/usr/bin/env python3
"""
Omnilingual Language Finder CLI
Beautiful, intuitive command-line interface
"""
import sys
import argparse
from pathlib import Path
from typing import List

try:
    from finder.core import LanguageFinder, Language
except ImportError:
    # Fallback for direct script execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from finder.core import LanguageFinder, Language


def format_language(lang: Language, verbose: bool = False) -> str:
    """Format language for display"""
    speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "?"
    
    if verbose:
        lines = [
            f"┌─ {lang.english_name} ({lang.code})",
            f"│  Native: {lang.native_name or 'N/A'}",
            f"│  Script: {lang.script_name} ({lang.script_code})",
            f"│  Speakers: {speakers}",
            f"│  Resource: {lang.resource_level}",
        ]
        
        if lang.countries:
            lines.append(f"│  Countries: {', '.join(lang.countries)}")
        if lang.regions:
            lines.append(f"│  Regions: {', '.join(lang.regions[:3])}")
        if lang.language_family:
            lines.append(f"│  Family: {lang.language_family}")
        
        lines.append("└─")
        return "\n".join(lines)
    else:
        # Compact format
        return f"{lang.code:20} {lang.english_name:30} {speakers:>15} speakers  [{lang.resource_level}]"


def cmd_search(args, finder: LanguageFinder):
    """Handle search command"""
    results = finder.search(
        name=args.name,
        country=args.country,
        region=args.region,
        script=args.script,
        family=args.family,
        resource_level=args.resource,
        min_speakers=args.min_speakers,
        limit=args.limit,
        sort_by=args.sort
    )
    
    if not results:
        print("❌ No languages found matching your criteria.")
        return
    
    print(f"✅ Found {len(results)} language(s):\n")
    
    for lang in results:
        print(format_language(lang, verbose=args.verbose))
        print()


def cmd_info(args, finder: LanguageFinder):
    """Handle info command"""
    lang = finder.get(args.code) or finder.find(args.code)
    
    if not lang:
        print(f"❌ Language not found: {args.code}")
        print("💡 Try: omnilingual-finder search --name '{}'".format(args.code))
        return
    
    # Rich display
    speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "Unknown"
    
    print(f"""
╔══════════════════════════════════════════════════════════
║ {lang.english_name}
╠══════════════════════════════════════════════════════════
║ Code:         {lang.code}
║ Native Name:  {lang.native_name or 'N/A'}
║ ISO 639-3:    {lang.iso_639_3}
║
║ Script:       {lang.script_name} ({lang.script_code})
║ Direction:    {lang.writing_direction}
║
║ Speakers:     {speakers}
║ Resource:     {lang.resource_level}
║ Data Source:  {lang.data_source}
║
║ Countries:    {', '.join(lang.countries) if lang.countries else 'N/A'}
║ Regions:      {', '.join(lang.regions[:5]) if lang.regions else 'N/A'}
║
║ Family:       {lang.language_family or 'N/A'}
    """)
    
    if lang.related_languages:
        print("║ Related:      " + ", ".join(lang.related_languages[:5]))
    
    if lang.wikipedia_code:
        print(f"║ Wikipedia:    {lang.wikipedia_code}")
    
    if lang.coordinates:
        print(f"║ Coordinates:  {lang.coordinates['lat']:.2f}, {lang.coordinates['lon']:.2f}")
    
    print("╚══════════════════════════════════════════════════════════\n")


def cmd_browse(args, finder: LanguageFinder):
    """Handle browse command"""
    regions = finder.browse_region(args.region)
    
    if not regions:
        print(f"❌ No languages found for region: {args.region}")
        return
    
    print(f"🗺️  Languages in {args.region}:\n")
    
    for region_name, langs in regions.items():
        print(f"📍 {region_name} ({len(langs)} languages)")
        
        # Show top languages by speakers
        top_langs = sorted(
            langs,
            key=lambda x: -x.speaker_count if x.speaker_count else 0
        )[:args.limit]
        
        for lang in top_langs:
            speakers = f"{lang.speaker_count:,}" if lang.speaker_count else "?"
            print(f"   • {lang.english_name:30} ({lang.code:15}) - {speakers} speakers")
        
        print()


def cmd_stats(args, finder: LanguageFinder):
    """Handle stats command"""
    stats = finder.statistics()
    
    print("""
╔═══════════════════════════════════════════════════
║ Omnilingual Language Finder Statistics
╠═══════════════════════════════════════════════════
    """)
    
    print(f"║ Total Languages:  {stats['total_languages']:,}")
    print(f"║ Total Scripts:    {stats['total_scripts']}")
    print(f"║ Total Families:   {stats['total_families']}")
    print(f"║ Total Countries:  {stats['total_countries']}")
    print(f"║ Total Speakers:   {stats['total_speakers']:,}")
    print("║")
    
    print("║ By Resource Level:")
    for item in stats['by_resource_level']:
        print(f"║   • {item['value']:12} {item['count']:4} languages")
    
    print("║")
    print("║ Top 10 Scripts:")
    for item in stats['by_script'][:10]:
        print(f"║   • {item['value']:12} {item['count']:4} languages")
    
    print("║")
    print("║ Top 10 Families:")
    for item in stats['by_family'][:10]:
        fam = item['value'] or 'Unknown'
        print(f"║   • {fam:30} {item['count']:4} languages")
    
    print("║")
    print("║ Top 10 Countries:")
    for item in stats['by_country'][:10]:
        print(f"║   • {item['country']:5} {item['count']:4} languages")
    
    print("╚═══════════════════════════════════════════════════\n")


def cmd_export(args, finder: LanguageFinder):
    """Handle export command"""
    # Build filter function
    filter_fn = None
    if args.filter:
        def filter_fn(lang: Language) -> bool:
            if args.filter == "high-resource":
                return lang.resource_level == "high"
            elif args.filter == "low-resource":
                return lang.resource_level in ["low", "zero-shot"]
            elif args.filter == "endangered":
                return lang.is_endangered
            elif args.filter.startswith("country:"):
                country = args.filter.split(":")[1]
                return country.upper() in lang.countries
            elif args.filter.startswith("script:"):
                script = args.filter.split(":")[1]
                return lang.script_code == script
            return True
    
    finder.export_json(args.output, filter_fn=filter_fn)
    print(f"✅ Exported to {args.output}")


def cmd_related(args, finder: LanguageFinder):
    """Handle related command"""
    lang = finder.get(args.code) or finder.find(args.code)
    
    if not lang:
        print(f"❌ Language not found: {args.code}")
        return
    
    print(f"🔗 Languages related to {lang.english_name} ({lang.code}):\n")
    
    related = finder.get_related(args.code, limit=args.limit)
    
    if not related:
        print("   No related languages found.")
        return
    
    for rel in related:
        speakers = f"{rel.speaker_count:,}" if rel.speaker_count else "?"
        print(f"   • {rel.english_name:30} ({rel.code:15}) - {speakers} speakers")
        print(f"     Family: {rel.language_family}, Script: {rel.script_name}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="🌍 Omnilingual Language Finder - Discover ASR language codes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find Hindi
  omnilingual-finder search --name Hindi
  
  # Languages in Maharashtra
  omnilingual-finder search --region Maharashtra
  
  # High-resource Devanagari languages in India
  omnilingual-finder search --country IN --script Devanagari --resource high
  
  # Get detailed info about a language
  omnilingual-finder info hin_Deva
  
  # Browse South Asian languages
  omnilingual-finder browse "South Asia"
  
  # Show statistics
  omnilingual-finder stats
        """
    )
    
    parser.add_argument(
        "--data-path",
        type=str,
        help="Path to languages.json (auto-discovers if not specified)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for languages")
    search_parser.add_argument("--name", help="Language name (fuzzy)")
    search_parser.add_argument("--country", help="Country (ISO2 or name)")
    search_parser.add_argument("--region", help="Region/state name")
    search_parser.add_argument("--script", help="Script name or code")
    search_parser.add_argument("--family", help="Language family")
    search_parser.add_argument("--resource", choices=["high", "medium", "low", "zero-shot"])
    search_parser.add_argument("--min-speakers", type=int, help="Minimum speaker count")
    search_parser.add_argument("--limit", type=int, default=20, help="Max results")
    search_parser.add_argument("--sort", choices=["speakers", "name", "resource", "family"], 
                              default="speakers")
    search_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Get detailed info about a language")
    info_parser.add_argument("code", help="Language code or name")
    
    # Browse command
    browse_parser = subparsers.add_parser("browse", help="Browse languages by region")
    browse_parser.add_argument("region", help="Region name (e.g., 'South Asia', 'India')")
    browse_parser.add_argument("--limit", type=int, default=10, help="Languages per region")
    
    # Stats command
    subparsers.add_parser("stats", help="Show statistics")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export languages to JSON")
    export_parser.add_argument("output", help="Output file path")
    export_parser.add_argument("--filter", help="Filter: high-resource, low-resource, endangered, country:XX, script:XXXX")
    
    # Related command
    related_parser = subparsers.add_parser("related", help="Find related languages")
    related_parser.add_argument("code", help="Language code")
    related_parser.add_argument("--limit", type=int, default=5, help="Max results")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize finder
    try:
        data_path = Path(args.data_path) if args.data_path else None
        finder = LanguageFinder(data_path)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\n💡 Run this first:")
        print("   python -m scripts.build_incremental --scripts Deva")
        print("   python -m scripts.build_index")
        sys.exit(1)
    
    # Route to command handler
    commands = {
        "search": cmd_search,
        "info": cmd_info,
        "browse": cmd_browse,
        "stats": cmd_stats,
        "export": cmd_export,
        "related": cmd_related,
    }
    
    if args.command in commands:
        commands[args.command](args, finder)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()