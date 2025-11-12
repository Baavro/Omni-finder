# # scripts/build_incremental.py
# from __future__ import annotations
# import asyncio, json, argparse, time
# from pathlib import Path
# from typing import List, Dict, Tuple, Set

# from extractor.supported import load_supported_codes
# from extractor.iso_cldr import load_iso_tables
# from extractor.wikidata import fetch_batch as wd_fetch, fetch_geo_batch
# from extractor.glottolog import for_glottocodes
# from extractor.merge import (
#     merge_language, val,
#     _resource_level_from_speakers, _data_source_heuristic,
#     _related_by_family_geo_selfscript,
# )

# OUT_PATH = Path("data/languages.json")
# PROGRESS_PATH = Path("data/progress.json")
# ISO_PATH = Path("sources/iso")
# CLDR_MAP = {"Deva": "Devanagari", "Latn": "Latin", "Arab": "Arabic"}

# def atomic_write(path: Path, payload: dict):
#     path.parent.mkdir(parents=True, exist_ok=True)
#     tmp = path.with_suffix(path.suffix + ".tmp")
#     tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
#     tmp.replace(path)

# def load_existing() -> Dict[str, dict]:
#     if OUT_PATH.exists():
#         return json.loads(OUT_PATH.read_text())
#     return {}

# def save_progress(done_codes: Set[str], total: int):
#     PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
#     data = {
#         "timestamp": int(time.time()),
#         "done": sorted(done_codes),
#         "done_count": len(done_codes),
#         "total": total,
#     }
#     atomic_write(PROGRESS_PATH, data)

# def split_parts(code: str) -> Tuple[str, str, str|None]:
#     parts = code.split("_")
#     iso = parts[0]
#     script = parts[1] if len(parts) > 1 else ""
#     variant = parts[2] if len(parts) > 2 else None
#     return iso, script, variant

# def filter_by_scripts(codes: List[str], allowed_scripts: Set[str]|None) -> List[str]:
#     if not allowed_scripts:
#         return codes
#     out = []
#     for c in codes:
#         _, script, _ = split_parts(c)
#         if script in allowed_scripts:
#             out.append(c)
#     return out

# async def process_batch(batch_codes: List[str], iso_tables) -> Dict[str, dict]:
#     # We may have multiple codes with same iso3 (different scripts/variants)
#     iso3s = sorted({split_parts(c)[0] for c in batch_codes})

#     # fetch wikidata core + geo
#     wd = await wd_fetch(iso3s)
#     geo = await fetch_geo_batch(iso3s)

#     # glottocodes from wd
#     glottos = [wd[k]["glottocode"] for k in wd if wd[k].get("glottocode")]
#     gl = await for_glottocodes(glottos)

#     out: Dict[str, dict] = {}
#     for code in batch_codes:
#         iso3, script, variant = split_parts(code)

#         # Ensure script name exists; if the model uses an uncommon script code just pass-through
#         cldr_map = dict(CLDR_MAP)
#         cldr_map.setdefault(script, script)

#         rec = merge_language(
#             iso3, script, iso_tables, wd, gl, cldr_map, geo=geo
#         )

#         # Keep the original code including variant if present (e.g., lld_Latn_gherd)
#         if variant:
#             rec["code"] = f"{iso3}_{script}_{variant}"

#         out[rec["code"]] = rec

#     # derivations
#     for k, row in out.items():
#         spk = (row.get("speaker_count") or {}).get("value")
#         row["resource_level"] = val(_resource_level_from_speakers(spk), "derived", 0.9)
#         row["data_source"]   = val(_data_source_heuristic(row["iso_639_3"]), "derived", 0.7)

#     # related languages (within batch for now; we’ll recompute globally after full build if needed)
#     for k in list(out.keys()):
#         out[k]["related_languages"] = _related_by_family_geo_selfscript(k, out)

#     return out

# async def main():
#     ap = argparse.ArgumentParser(description="Incremental metadata builder for Omnilingual Finder")
#     ap.add_argument("--scripts", type=str, default="Deva",
#                     help="Comma-separated script codes to include (e.g., 'Deva,Latn,Arab'). "
#                          "Use '*' for all.")
#     ap.add_argument("--batch-size", type=int, default=25)
#     ap.add_argument("--limit", type=int, default=0, help="Max languages to process this run (0 = no limit)")
#     ap.add_argument("--out", type=str, default=str(OUT_PATH))
#     args = ap.parse_args()

#     out_path = Path(args.out)

#     # 1) load universe of supported codes
#     all_codes = load_supported_codes()

#     # 2) filter by scripts
#     allowed = None if args.scripts.strip() == "*" else set(s.strip() for s in args.scripts.split(","))
#     target_codes = filter_by_scripts(all_codes, allowed)

#     # 3) resume: load existing output and skip done codes
#     existing = {}
#     if out_path.exists():
#         existing = json.loads(out_path.read_text())

#     done_codes = set(existing.keys())
#     # Normalize codes so variant and non-variant forms are comparable
#     remaining = [c for c in target_codes if c not in done_codes]

#     # 4) optionally cap total this run
#     if args.limit and args.limit > 0:
#         remaining = remaining[:args.limit]

#     total_this_run = len(remaining)
#     print(f"Total supported codes: {len(all_codes)} | After script filter: {len(target_codes)} | To process now: {total_this_run}")

#     if total_this_run == 0:
#         print("Nothing to do. (Everything already built for selected scripts.)")
#         return

#     # 5) shared data
#     iso_tables = load_iso_tables(ISO_PATH)

#     # 6) batch loop with checkpointing
#     start = 0
#     while start < len(remaining):
#         batch_codes = remaining[start:start + args.batch_size]
#         print(f"🧩 Batch {start//args.batch_size + 1}: {len(batch_codes)} items")

#         try:
#             batch_out = await process_batch(batch_codes, iso_tables)
#         except Exception as e:
#             print(f"Batch failed: {e}")
#             # save progress so far and stop
#             atomic_write(out_path, existing)
#             save_progress(done_codes, len(target_codes))
#             raise

#         # merge into existing and write atomically
#         existing.update(batch_out)
#         atomic_write(out_path, existing)

#         # update progress
#         done_codes.update(batch_out.keys())
#         save_progress(done_codes, len(target_codes))

#         start += args.batch_size
#         # be nice to public endpoints
#         await asyncio.sleep(0.5)

#     print(f"✅ Done. Total records in {out_path}: {len(existing)}")

# if __name__ == "__main__":
#     asyncio.run(main())


# # scripts/build_incremental.py
# from __future__ import annotations
# import asyncio, json, argparse, time
# from pathlib import Path
# from typing import List, Dict, Tuple, Set

# from extractor.supported import load_supported_codes
# from extractor.iso_cldr import load_iso_tables
# from extractor.wikidata import fetch_batch as wd_fetch, fetch_geo_batch
# from extractor.glottolog import for_glottocodes
# from extractor.merge import (
#     merge_language, val,
#     _resource_level_from_speakers, _data_source_heuristic,
#     _related_by_family_geo_selfscript,
# )

# OUT_PATH = Path("data/languages.json")
# PROGRESS_PATH = Path("data/progress.json")
# SKIPPED_PATH = Path("data/skipped.json")
# ISO_PATH = Path("sources/iso")
# CLDR_MAP = {"Deva": "Devanagari", "Latn": "Latin", "Arab": "Arabic"}

# def atomic_write(path: Path, payload: dict):
#     path.parent.mkdir(parents=True, exist_ok=True)
#     tmp = path.with_suffix(path.suffix + ".tmp")
#     tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
#     tmp.replace(path)

# def load_existing(path: Path) -> Dict[str, dict]:
#     if path.exists():
#         return json.loads(path.read_text())
#     return {}

# def save_progress(done_codes: Set[str], total: int):
#     PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
#     data = {
#         "timestamp": int(time.time()),
#         "done": sorted(done_codes),
#         "done_count": len(done_codes),
#         "total": total,
#     }
#     atomic_write(PROGRESS_PATH, data)

# def load_skiplist(skiplist_path: str | None) -> Set[str]:
#     sl: Set[str] = set()
#     if not skiplist_path:
#         return sl
#     p = Path(skiplist_path)
#     if not p.exists():
#         return sl
#     for line in p.read_text().splitlines():
#         s = line.strip()
#         if not s or s.startswith("#"):
#             continue
#         sl.add(s)
#     return sl

# def split_parts(code: str) -> Tuple[str, str, str|None]:
#     parts = code.split("_")
#     iso = parts[0]
#     script = parts[1] if len(parts) > 1 else ""
#     variant = parts[2] if len(parts) > 2 else None
#     return iso, script, variant

# def filter_by_scripts(codes: List[str], allowed_scripts: Set[str]|None) -> List[str]:
#     if not allowed_scripts:
#         return codes
#     out = []
#     for c in codes:
#         _, script, _ = split_parts(c)
#         if script in allowed_scripts:
#             out.append(c)
#     return out

# async def process_batch(batch_codes: List[str], iso_tables) -> Dict[str, dict]:
#     # We may have multiple codes with same iso3 (different scripts/variants)
#     iso3s = sorted({split_parts(c)[0] for c in batch_codes})

#     # fetch wikidata core + geo
#     wd = await wd_fetch(iso3s)
#     geo = await fetch_geo_batch(iso3s)

#     # glottocodes from wd
#     glottos = [wd[k]["glottocode"] for k in wd if wd[k].get("glottocode")]
#     gl = await for_glottocodes(glottos)

#     out: Dict[str, dict] = {}
#     for code in batch_codes:
#         iso3, script, variant = split_parts(code)

#         # Ensure script name exists; if the model uses an uncommon script code just pass-through
#         cldr_map = dict(CLDR_MAP)
#         cldr_map.setdefault(script, script)

#         rec = merge_language(
#             iso3, script, iso_tables, wd, gl, cldr_map, geo=geo
#         )

#         # Keep the original code including variant if present (e.g., lld_Latn_gherd)
#         if variant:
#             rec["code"] = f"{iso3}_{script}_{variant}"

#         out[rec["code"]] = rec

#     # derivations
#     for k, row in out.items():
#         spk = (row.get("speaker_count") or {}).get("value")
#         row["resource_level"] = val(_resource_level_from_speakers(spk), "derived", 0.9)
#         row["data_source"]   = val(_data_source_heuristic(row["iso_639_3"]), "derived", 0.7)

#     # related languages (within batch for now; can recompute globally later)
#     for k in list(out.keys()):
#         out[k]["related_languages"] = _related_by_family_geo_selfscript(k, out)

#     return out

# def mark_skipped(skipped: Dict[str, list], batch_codes: List[str], reason: str):
#     skipped.setdefault("batches", []).append({
#         "timestamp": int(time.time()),
#         "reason": reason,
#         "codes": batch_codes,
#     })
#     atomic_write(SKIPPED_PATH, skipped)

# async def main():
#     ap = argparse.ArgumentParser(description="Incremental metadata builder for Omnilingual Finder")
#     ap.add_argument("--scripts", type=str, default="Deva",
#                     help="Comma-separated script codes to include (e.g., 'Deva,Latn,Arab'). Use '*' for all.")
#     ap.add_argument("--batch-size", type=int, default=25)
#     ap.add_argument("--limit", type=int, default=0, help="Max languages to process this run (0 = no limit)")
#     ap.add_argument("--out", type=str, default=str(OUT_PATH))
#     # manual/auto skip controls
#     ap.add_argument("--skip-trigger", type=str, default="data/skip.now",
#                     help="Touch this file during a run to skip the current batch.")
#     ap.add_argument("--max-batch-seconds", type=float, default=120.0,
#                     help="Auto-skip a batch if it exceeds this wall-clock time.")
#     ap.add_argument("--skiplist", type=str, default="",
#                     help="Path to a file listing codes or ISO3 to always skip (one per line).")
#     args = ap.parse_args()

#     out_path = Path(args.out)
#     skip_trigger_path = Path(args.skip_trigger)

#     # 1) load universe of supported codes
#     all_codes = load_supported_codes()

#     # 2) filter by scripts
#     allowed = None if args.scripts.strip() == "*" else set(s.strip() for s in args.scripts.split(","))
#     target_codes = filter_by_scripts(all_codes, allowed)

#     # 2.5) skiplist (full code or bare ISO3)
#     skiplist = load_skiplist(args.skiplist)
#     if skiplist:
#         def want(c: str) -> bool:
#             iso, _, _ = split_parts(c)
#             return not (c in skiplist or iso in skiplist)
#         target_codes = [c for c in target_codes if want(c)]

#     # 3) resume: load existing output and skip done codes
#     existing = load_existing(out_path)

#     done_codes = set(existing.keys())
#     remaining = [c for c in target_codes if c not in done_codes]

#     # 4) optionally cap total this run
#     if args.limit and args.limit > 0:
#         remaining = remaining[:args.limit]

#     total_this_run = len(remaining)
#     print(f"Total supported codes: {len(all_codes)} | After script filter: {len(target_codes)} | To process now: {total_this_run}")

#     if total_this_run == 0:
#         print("Nothing to do. (Everything already built for selected scripts.)")
#         return

#     # 5) shared data
#     iso_tables = load_iso_tables(ISO_PATH)

#     # skipped registry
#     skipped_registry = load_existing(SKIPPED_PATH)

#     # 6) batch loop with checkpointing + manual/auto skip
#     start = 0
#     while start < len(remaining):
#         batch_codes = remaining[start:start + args.batch_size]
#         batch_num = start // args.batch_size + 1
#         print(f"🧩 Batch {batch_num}: {len(batch_codes)} items")

#         # manual skip button: touch data/skip.now to skip this batch instantly
#         if skip_trigger_path.exists():
#             skip_trigger_path.unlink(missing_ok=True)
#             print(f"⏭️  Manual skip triggered → skipping batch {batch_num}")
#             mark_skipped(skipped_registry, batch_codes, reason="manual-trigger")
#             start += args.batch_size
#             continue

#         try:
#             # run the batch with a wall-clock guard
#             batch_out = await asyncio.wait_for(
#                 process_batch(batch_codes, iso_tables),
#                 timeout=args.max_batch_seconds
#             )
#         except asyncio.TimeoutError:
#             print(f"⏳ Batch {batch_num} exceeded {args.max_batch_seconds}s → skipping")
#             mark_skipped(skipped_registry, batch_codes, reason="timeout")
#             # write current state and continue
#             atomic_write(out_path, existing)
#             save_progress(done_codes, len(target_codes))
#             start += args.batch_size
#             continue
#         except Exception as e:
#             print(f"Batch {batch_num} failed: {e}")
#             # mark skipped but keep going
#             mark_skipped(skipped_registry, batch_codes, reason=f"error:{type(e).__name__}")
#             atomic_write(out_path, existing)
#             save_progress(done_codes, len(target_codes))
#             start += args.batch_size
#             continue

#         # merge into existing and write atomically
#         existing.update(batch_out)
#         atomic_write(out_path, existing)

#         # update progress
#         done_codes.update(batch_out.keys())
#         save_progress(done_codes, len(target_codes))

#         start += args.batch_size
#         # be nice to public endpoints
#         await asyncio.sleep(0.5)

#     print(f"✅ Done. Total records in {out_path}: {len(existing)}")
#     if SKIPPED_PATH.exists():
#         print(f"ℹ️  Skipped details saved to {SKIPPED_PATH}")

# if __name__ == "__main__":
#     asyncio.run(main())

# # scripts/build_incremental.py
# from __future__ import annotations
# import asyncio, json, argparse, time
# from pathlib import Path
# from typing import List, Dict, Tuple, Set

# from extractor.supported import load_supported_codes
# from extractor.iso_cldr import load_iso_tables
# from extractor.wikidata import fetch_batch as wd_fetch, fetch_geo_batch
# from extractor.glottolog import for_glottocodes
# from extractor.merge import (
#     merge_language, val,
#     _resource_level_from_speakers, _data_source_heuristic,
#     _related_by_family_geo_selfscript,
# )
# from extractor.profiler import get_profiler, time_block, checkpoint, print_summary, export_json as export_profile

# OUT_PATH = Path("data/languages.json")
# PROGRESS_PATH = Path("data/progress.json")
# SKIPPED_PATH = Path("data/skipped.json")
# PROFILE_PATH = Path("data/profiling.json")
# ISO_PATH = Path("sources/iso")
# CLDR_MAP = {"Deva": "Devanagari", "Latn": "Latin", "Arab": "Arabic"}


# def atomic_write(path: Path, payload: dict):
#     path.parent.mkdir(parents=True, exist_ok=True)
#     tmp = path.with_suffix(path.suffix + ".tmp")
#     tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
#     tmp.replace(path)

# def load_existing(path: Path) -> Dict[str, dict]:
#     if path.exists():
#         return json.loads(path.read_text())
#     return {}

# def save_progress(done_codes: Set[str], total: int):
#     PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
#     data = {
#         "timestamp": int(time.time()),
#         "done": sorted(done_codes),
#         "done_count": len(done_codes),
#         "total": total,
#     }
#     atomic_write(PROGRESS_PATH, data)

# def load_skiplist(skiplist_path: str | None) -> Set[str]:
#     sl: Set[str] = set()
#     if not skiplist_path:
#         return sl
#     p = Path(skiplist_path)
#     if not p.exists():
#         return sl
#     for line in p.read_text().splitlines():
#         s = line.strip()
#         if not s or s.startswith("#"):
#             continue
#         sl.add(s)
#     return sl

# def split_parts(code: str) -> Tuple[str, str, str|None]:
#     parts = code.split("_")
#     iso = parts[0]
#     script = parts[1] if len(parts) > 1 else ""
#     variant = parts[2] if len(parts) > 2 else None
#     return iso, script, variant

# def filter_by_scripts(codes: List[str], allowed_scripts: Set[str]|None) -> List[str]:
#     if not allowed_scripts:
#         return codes
#     out = []
#     for c in codes:
#         _, script, _ = split_parts(c)
#         if script in allowed_scripts:
#             out.append(c)
#     return out

# async def process_batch(batch_codes: List[str], iso_tables, batch_num: int) -> Dict[str, dict]:
#     """Process a batch of language codes with detailed profiling"""
#     with time_block("process_batch", batch_num=batch_num, num_codes=len(batch_codes)):
#         # We may have multiple codes with same iso3 (different scripts/variants)
#         with time_block("extract_iso3_codes"):
#             iso3s = sorted({split_parts(c)[0] for c in batch_codes})
#         checkpoint("iso3_codes_extracted", num_unique=len(iso3s), from_codes=len(batch_codes))

#         # Fetch wikidata core
#         print(f"  📡 Fetching Wikidata core for {len(iso3s)} ISO codes...")
#         with time_block("fetch_wikidata_core", num_iso3=len(iso3s)):
#             wd = await wd_fetch(iso3s)
#         checkpoint("wikidata_core_complete", results=len(wd), requested=len(iso3s))
        
#         # Fetch geo
#         print(f"  🌍 Fetching geographic data...")
#         with time_block("fetch_geo_data", num_iso3=len(iso3s)):
#             geo = await fetch_geo_batch(iso3s)
#         checkpoint("geo_data_complete", results=len(geo), requested=len(iso3s))

#         # Glottocodes from wd
#         with time_block("extract_glottocodes"):
#             glottos = [wd[k]["glottocode"] for k in wd if wd[k].get("glottocode")]
#         checkpoint("glottocodes_extracted", num_glottocodes=len(glottos))
        
#         print(f"  🗂️  Fetching Glottolog data for {len(glottos)} codes...")
#         with time_block("fetch_glottolog", num_glottocodes=len(glottos)):
#             gl = await for_glottocodes(glottos)
#         checkpoint("glottolog_complete", results=len(gl), requested=len(glottos))

#         # Merge data for each language
#         print(f"  🔀 Merging data for {len(batch_codes)} languages...")
#         out: Dict[str, dict] = {}
#         with time_block("merge_all_languages", num_codes=len(batch_codes)):
#             for code in batch_codes:
#                 with time_block("merge_single_language"):
#                     iso3, script, variant = split_parts(code)

#                     # Ensure script name exists
#                     cldr_map = dict(CLDR_MAP)
#                     cldr_map.setdefault(script, script)

#                     rec = merge_language(
#                         iso3, script, iso_tables, wd, gl, cldr_map, geo=geo
#                     )

#                     # Keep the original code including variant if present
#                     if variant:
#                         rec["code"] = f"{iso3}_{script}_{variant}"

#                     out[rec["code"]] = rec

#         # Compute derivations
#         print(f"  🧮 Computing resource levels and related languages...")
#         with time_block("compute_derivations", num_langs=len(out)):
#             for k, row in out.items():
#                 spk = (row.get("speaker_count") or {}).get("value")
#                 row["resource_level"] = val(_resource_level_from_speakers(spk), "derived", 0.9)
#                 row["data_source"]   = val(_data_source_heuristic(row["iso_639_3"]), "derived", 0.7)

#             # Related languages (within batch for now; can recompute globally later)
#             for k in list(out.keys()):
#                 out[k]["related_languages"] = _related_by_family_geo_selfscript(k, out)

#         checkpoint("batch_complete", num_languages=len(out))
#         return out

# def mark_skipped(skipped: Dict[str, list], batch_codes: List[str], reason: str):
#     skipped.setdefault("batches", []).append({
#         "timestamp": int(time.time()),
#         "reason": reason,
#         "codes": batch_codes,
#     })
#     atomic_write(SKIPPED_PATH, skipped)

# def print_progress_bar(current: int, total: int, width: int = 50):
#     """Print a nice progress bar"""
#     filled = int(width * current / total) if total > 0 else 0
#     bar = "█" * filled + "░" * (width - filled)
#     percent = 100 * current / total if total > 0 else 0
#     print(f"\r  Progress: |{bar}| {current}/{total} ({percent:.1f}%)", end="", flush=True)

# async def main():
#     profiler = get_profiler()
    
#     with time_block("full_build"):
#         ap = argparse.ArgumentParser(description="Incremental metadata builder for Omnilingual Finder")
#         ap.add_argument("--scripts", type=str, default="Deva",
#                         help="Comma-separated script codes to include (e.g., 'Deva,Latn,Arab'). Use '*' for all.")
#         ap.add_argument("--batch-size", type=int, default=25)
#         ap.add_argument("--limit", type=int, default=0, help="Max languages to process this run (0 = no limit)")
#         ap.add_argument("--out", type=str, default=str(OUT_PATH))
#         ap.add_argument("--skip-trigger", type=str, default="data/skip.now",
#                         help="Touch this file during a run to skip the current batch.")
#         ap.add_argument("--max-batch-seconds", type=float, default=120.0,
#                         help="Auto-skip a batch if it exceeds this wall-clock time.")
#         ap.add_argument("--skiplist", type=str, default="",
#                         help="Path to a file listing codes or ISO3 to always skip (one per line).")
#         ap.add_argument("--profile", action="store_true",
#                         help="Export detailed profiling data at the end")
#         args = ap.parse_args()

#         out_path = Path(args.out)
#         skip_trigger_path = Path(args.skip_trigger)

#         print("🚀 Starting Omnilingual Finder Data Build")
#         print("=" * 80)

#         # 1) Load universe of supported codes
#         with time_block("load_supported_codes"):
#             all_codes = load_supported_codes()
#         checkpoint("supported_codes_loaded", total=len(all_codes))

#         # 2) Filter by scripts
#         with time_block("filter_by_scripts"):
#             allowed = None if args.scripts.strip() == "*" else set(s.strip() for s in args.scripts.split(","))
#             target_codes = filter_by_scripts(all_codes, allowed)
#         checkpoint("scripts_filtered", total=len(target_codes), scripts=args.scripts)

#         # 2.5) Skiplist
#         with time_block("load_skiplist"):
#             skiplist = load_skiplist(args.skiplist)
#             if skiplist:
#                 def want(c: str) -> bool:
#                     iso, _, _ = split_parts(c)
#                     return not (c in skiplist or iso in skiplist)
#                 target_codes = [c for c in target_codes if want(c)]
#         checkpoint("skiplist_applied", skipped=len(skiplist), remaining=len(target_codes))

#         # 3) Resume: load existing output and skip done codes
#         with time_block("load_existing_data"):
#             existing = load_existing(out_path)
#         checkpoint("existing_data_loaded", existing_count=len(existing))

#         done_codes = set(existing.keys())
#         remaining = [c for c in target_codes if c not in done_codes]

#         # 4) Optionally cap total this run
#         if args.limit and args.limit > 0:
#             remaining = remaining[:args.limit]

#         total_this_run = len(remaining)
        
#         print(f"\n📊 Build Configuration:")
#         print(f"   Total supported:     {len(all_codes):4} languages")
#         print(f"   After script filter: {len(target_codes):4} languages")
#         print(f"   Already built:       {len(done_codes):4} languages")
#         print(f"   To process now:      {total_this_run:4} languages")
#         print(f"   Batch size:          {args.batch_size}")
#         print(f"   Max batch time:      {args.max_batch_seconds}s")
#         print("=" * 80)

#         if total_this_run == 0:
#             print("\n✅ Nothing to do. (Everything already built for selected scripts.)")
#             return

#         # 5) Shared data
#         print("\n📚 Loading ISO 639-3 tables...")
#         with time_block("load_iso_tables"):
#             iso_tables = load_iso_tables(ISO_PATH)
#         checkpoint("iso_tables_loaded")

#         # Skipped registry
#         skipped_registry = load_existing(SKIPPED_PATH)

#         # 6) Batch loop with checkpointing + manual/auto skip
#         print("\n🔄 Processing batches...\n")
#         start = 0
#         num_batches = (len(remaining) + args.batch_size - 1) // args.batch_size
        
#         while start < len(remaining):
#             batch_codes = remaining[start:start + args.batch_size]
#             batch_num = start // args.batch_size + 1
            
#             print(f"\n{'='*80}")
#             print(f"🧩 Batch {batch_num}/{num_batches}: {len(batch_codes)} languages")
#             print(f"{'='*80}")
            
#             # Print some sample codes
#             print(f"   Codes: {', '.join(batch_codes[:5])}" + (" ..." if len(batch_codes) > 5 else ""))

#             # Manual skip button: touch data/skip.now to skip this batch instantly
#             if skip_trigger_path.exists():
#                 skip_trigger_path.unlink(missing_ok=True)
#                 print(f"⏭️  Manual skip triggered → skipping batch {batch_num}")
#                 mark_skipped(skipped_registry, batch_codes, reason="manual-trigger")
#                 start += args.batch_size
#                 continue

#             batch_start_time = time.time()
            
#             try:
#                 # Run the batch with a wall-clock guard
#                 batch_out = await asyncio.wait_for(
#                     process_batch(batch_codes, iso_tables, batch_num),
#                     timeout=args.max_batch_seconds
#                 )
                
#                 batch_duration = time.time() - batch_start_time
#                 print(f"\n  ✅ Batch completed in {batch_duration:.1f}s")
                
#             except asyncio.TimeoutError:
#                 batch_duration = time.time() - batch_start_time
#                 print(f"\n  ⏳ Batch {batch_num} exceeded {args.max_batch_seconds}s → skipping")
#                 mark_skipped(skipped_registry, batch_codes, reason="timeout")
#                 # Write current state and continue
#                 atomic_write(out_path, existing)
#                 save_progress(done_codes, len(target_codes))
#                 start += args.batch_size
#                 continue
                
#             except Exception as e:
#                 batch_duration = time.time() - batch_start_time
#                 print(f"\n  ❌ Batch {batch_num} failed: {e}")
#                 # Mark skipped but keep going
#                 mark_skipped(skipped_registry, batch_codes, reason=f"error:{type(e).__name__}")
#                 atomic_write(out_path, existing)
#                 save_progress(done_codes, len(target_codes))
#                 start += args.batch_size
#                 continue

#             # Merge into existing and write atomically
#             print(f"  💾 Saving {len(batch_out)} languages...")
#             with time_block("save_batch_results"):
#                 existing.update(batch_out)
#                 atomic_write(out_path, existing)

#             # Update progress
#             done_codes.update(batch_out.keys())
#             save_progress(done_codes, len(target_codes))
            
#             # Print overall progress
#             print_progress_bar(len(done_codes), len(target_codes))

#             start += args.batch_size
            
#             # Be nice to public endpoints
#             if start < len(remaining):
#                 print(f"\n  😴 Pausing 0.5s before next batch...")
#                 await asyncio.sleep(0.5)

#         print(f"\n\n{'='*80}")
#         print(f"✅ Build Complete!")
#         print(f"{'='*80}")
#         print(f"   Total records in {out_path}: {len(existing)}")
#         if SKIPPED_PATH.exists():
#             skipped_count = len(load_existing(SKIPPED_PATH).get("batches", []))
#             print(f"   Skipped batches: {skipped_count} (see {SKIPPED_PATH})")
#         print(f"{'='*80}\n")

#         # Print profiling summary
#         print_summary(top_n=30)
        
#         # Optionally export detailed profiling
#         if args.profile:
#             export_profile(PROFILE_PATH)
#             print(f"📊 Detailed profiling exported to {PROFILE_PATH}")

# if __name__ == "__main__":
#     asyncio.run(main())

# scripts/build_incremental.py
from __future__ import annotations
import asyncio, json, argparse, time
from pathlib import Path
from typing import List, Dict, Tuple, Set

from extractor.supported import load_supported_codes
from extractor.iso_cldr import load_iso_tables
from extractor.wikidata import fetch_batch as wd_fetch, fetch_geo_batch
from extractor.glottolog import for_glottocodes
from extractor.merge import (
    merge_language, val,
    _resource_level_from_speakers, _data_source_heuristic,
    _related_by_family_geo_selfscript,
)
from extractor.profiler import get_profiler, time_block, checkpoint, print_summary, export_json as export_profile

OUT_PATH = Path("data/languages.json")
PROGRESS_PATH = Path("data/progress.json")
SKIPPED_PATH = Path("data/skipped.json")
PROFILE_PATH = Path("data/profiling.json")
ISO_PATH = Path("sources/iso")
CLDR_MAP = {"Deva": "Devanagari", "Latn": "Latin", "Arab": "Arabic"}


def atomic_write(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp.replace(path)

def load_existing(path: Path) -> Dict[str, dict]:
    if path.exists():
        return json.loads(path.read_text())
    return {}

def save_progress(done_codes: Set[str], total: int):
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": int(time.time()),
        "done": sorted(done_codes),
        "done_count": len(done_codes),
        "total": total,
    }
    atomic_write(PROGRESS_PATH, data)

def load_skiplist(skiplist_path: str | None) -> Set[str]:
    sl: Set[str] = set()
    if not skiplist_path:
        return sl
    p = Path(skiplist_path)
    if not p.exists():
        return sl
    for line in p.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        sl.add(s)
    return sl

def split_parts(code: str) -> Tuple[str, str, str|None]:
    """
    Split language code into parts.
    
    IMPORTANT: Handle 'nan' specially - it's a valid ISO 639-3 code (Min Nan language)
    but Python/pandas interpret it as NaN (Not a Number)
    """
    # Ensure code is a string (handles pandas NaN issue)
    if not isinstance(code, str):
        # If it's actually NaN/None, skip it
        if code is None or (isinstance(code, float) and code != code):  # NaN check
            raise ValueError(f"Invalid code: {code}")
        code = str(code)
    
    parts = code.split("_")
    iso = parts[0]
    script = parts[1] if len(parts) > 1 else ""
    variant = parts[2] if len(parts) > 2 else None
    return iso, script, variant

def filter_by_scripts(codes: List[str], allowed_scripts: Set[str]|None) -> List[str]:
    if not allowed_scripts:
        return codes
    out = []
    for c in codes:
        _, script, _ = split_parts(c)
        if script in allowed_scripts:
            out.append(c)
    return out

async def process_batch(batch_codes: List[str], iso_tables, batch_num: int, skip_geo: bool = False) -> Dict[str, dict]:
    """Process a batch of language codes with detailed profiling"""
    with time_block("process_batch", batch_num=batch_num, num_codes=len(batch_codes)):
        # We may have multiple codes with same iso3 (different scripts/variants)
        with time_block("extract_iso3_codes"):
            iso3s = sorted({split_parts(c)[0] for c in batch_codes})
        checkpoint("iso3_codes_extracted", num_unique=len(iso3s), from_codes=len(batch_codes))

        # Fetch wikidata core
        print(f"  📡 Fetching Wikidata core for {len(iso3s)} ISO codes...")
        with time_block("fetch_wikidata_core", num_iso3=len(iso3s)):
            wd = await wd_fetch(iso3s)
        checkpoint("wikidata_core_complete", results=len(wd), requested=len(iso3s))
        
        # Fetch geo (optional)
        geo = {}
        if skip_geo:
            print(f"  ⏭️  Skipping geographic data (--skip-geo enabled)")
            checkpoint("geo_data_skipped", reason="user_option")
        else:
            print(f"  🌍 Fetching geographic data...")
            with time_block("fetch_geo_data", num_iso3=len(iso3s)):
                try:
                    geo = await fetch_geo_batch(iso3s, timeout=90.0, chunk_size=3, retries=2)
                    checkpoint("geo_data_complete", results=len(geo), requested=len(iso3s))
                except Exception as e:
                    print(f"  ⚠️  Geographic data failed: {type(e).__name__}")
                    print(f"     Continuing without geo data (can be added later)")
                    checkpoint("geo_data_failed", error=type(e).__name__)
                    geo = {}

        # Glottocodes from wd
        with time_block("extract_glottocodes"):
            glottos = [wd[k]["glottocode"] for k in wd if wd[k].get("glottocode")]
        checkpoint("glottocodes_extracted", num_glottocodes=len(glottos))
        
        print(f"  🗂️  Fetching Glottolog data for {len(glottos)} codes...")
        with time_block("fetch_glottolog", num_glottocodes=len(glottos)):
            gl = await for_glottocodes(glottos)
        checkpoint("glottolog_complete", results=len(gl), requested=len(glottos))

        # Merge data for each language
        print(f"  🔀 Merging data for {len(batch_codes)} languages...")
        out: Dict[str, dict] = {}
        with time_block("merge_all_languages", num_codes=len(batch_codes)):
            for code in batch_codes:
                with time_block("merge_single_language"):
                    try:
                        iso3, script, variant = split_parts(code)
                    except ValueError as e:
                        print(f"    ⚠️  Skipping invalid code: {code} ({e})")
                        continue

                    # Ensure script name exists
                    cldr_map = dict(CLDR_MAP)
                    cldr_map.setdefault(script, script)

                    try:
                        rec = merge_language(
                            iso3, script, iso_tables, wd, gl, cldr_map, geo=geo
                        )

                        # Keep the original code including variant if present
                        if variant:
                            rec["code"] = f"{iso3}_{script}_{variant}"

                        out[rec["code"]] = rec
                    except Exception as e:
                        print(f"    ⚠️  Failed to merge {code}: {type(e).__name__} - {str(e)[:100]}")
                        checkpoint("merge_failed", code=code, error=type(e).__name__)
                        continue

        # Compute derivations
        print(f"  🧮 Computing resource levels and related languages...")
        with time_block("compute_derivations", num_langs=len(out)):
            for k, row in out.items():
                spk = (row.get("speaker_count") or {}).get("value")
                row["resource_level"] = val(_resource_level_from_speakers(spk), "derived", 0.9)
                row["data_source"]   = val(_data_source_heuristic(row["iso_639_3"]), "derived", 0.7)

            # Related languages (within batch for now; can recompute globally later)
            for k in list(out.keys()):
                out[k]["related_languages"] = _related_by_family_geo_selfscript(k, out)

        checkpoint("batch_complete", num_languages=len(out))
        return out

def mark_skipped(skipped: Dict[str, list], batch_codes: List[str], reason: str):
    skipped.setdefault("batches", []).append({
        "timestamp": int(time.time()),
        "reason": reason,
        "codes": batch_codes,
    })
    atomic_write(SKIPPED_PATH, skipped)

def print_progress_bar(current: int, total: int, width: int = 50):
    """Print a nice progress bar"""
    filled = int(width * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (width - filled)
    percent = 100 * current / total if total > 0 else 0
    print(f"\r  Progress: |{bar}| {current}/{total} ({percent:.1f}%)", end="", flush=True)

async def main():
    profiler = get_profiler()
    
    with time_block("full_build"):
        ap = argparse.ArgumentParser(description="Incremental metadata builder for Omnilingual Finder")
        ap.add_argument("--scripts", type=str, default="Deva",
                        help="Comma-separated script codes to include (e.g., 'Deva,Latn,Arab'). Use '*' for all.")
        ap.add_argument("--batch-size", type=int, default=25)
        ap.add_argument("--limit", type=int, default=0, help="Max languages to process this run (0 = no limit)")
        ap.add_argument("--out", type=str, default=str(OUT_PATH))
        ap.add_argument("--skip-trigger", type=str, default="data/skip.now",
                        help="Touch this file during a run to skip the current batch.")
        ap.add_argument("--max-batch-seconds", type=float, default=120.0,
                        help="Auto-skip a batch if it exceeds this wall-clock time.")
        ap.add_argument("--skiplist", type=str, default="",
                        help="Path to a file listing codes or ISO3 to always skip (one per line).")
        ap.add_argument("--skip-geo", action="store_true",
                        help="Skip geographic data fetching (faster, can be added later)")
        ap.add_argument("--profile", action="store_true",
                        help="Export detailed profiling data at the end")
        args = ap.parse_args()

        out_path = Path(args.out)
        skip_trigger_path = Path(args.skip_trigger)

        print("🚀 Starting Omnilingual Finder Data Build")
        print("=" * 80)

        # 1) Load universe of supported codes
        with time_block("load_supported_codes"):
            all_codes = load_supported_codes()
        checkpoint("supported_codes_loaded", total=len(all_codes))

        # 2) Filter by scripts
        with time_block("filter_by_scripts"):
            allowed = None if args.scripts.strip() == "*" else set(s.strip() for s in args.scripts.split(","))
            target_codes = filter_by_scripts(all_codes, allowed)
        checkpoint("scripts_filtered", total=len(target_codes), scripts=args.scripts)

        # 2.5) Skiplist
        with time_block("load_skiplist"):
            skiplist = load_skiplist(args.skiplist)
            if skiplist:
                def want(c: str) -> bool:
                    iso, _, _ = split_parts(c)
                    return not (c in skiplist or iso in skiplist)
                target_codes = [c for c in target_codes if want(c)]
        checkpoint("skiplist_applied", skipped=len(skiplist), remaining=len(target_codes))

        # 3) Resume: load existing output and skip done codes
        with time_block("load_existing_data"):
            existing = load_existing(out_path)
        checkpoint("existing_data_loaded", existing_count=len(existing))

        done_codes = set(existing.keys())
        remaining = [c for c in target_codes if c not in done_codes]

        # 4) Optionally cap total this run
        if args.limit and args.limit > 0:
            remaining = remaining[:args.limit]

        total_this_run = len(remaining)
        
        print(f"\n📊 Build Configuration:")
        print(f"   Total supported:     {len(all_codes):4} languages")
        print(f"   After script filter: {len(target_codes):4} languages")
        print(f"   Already built:       {len(done_codes):4} languages")
        print(f"   To process now:      {total_this_run:4} languages")
        print(f"   Batch size:          {args.batch_size}")
        print(f"   Max batch time:      {args.max_batch_seconds}s")
        print("=" * 80)

        if total_this_run == 0:
            print("\n✅ Nothing to do. (Everything already built for selected scripts.)")
            return

        # 5) Shared data
        print("\n📚 Loading ISO 639-3 tables...")
        with time_block("load_iso_tables"):
            iso_tables = load_iso_tables(ISO_PATH)
        checkpoint("iso_tables_loaded")

        # Skipped registry
        skipped_registry = load_existing(SKIPPED_PATH)

        # 6) Batch loop with checkpointing + manual/auto skip
        print("\n🔄 Processing batches...\n")
        start = 0
        num_batches = (len(remaining) + args.batch_size - 1) // args.batch_size
        
        while start < len(remaining):
            batch_codes = remaining[start:start + args.batch_size]
            batch_num = start // args.batch_size + 1
            
            print(f"\n{'='*80}")
            print(f"🧩 Batch {batch_num}/{num_batches}: {len(batch_codes)} languages")
            print(f"{'='*80}")
            
            # Print some sample codes
            print(f"   Codes: {', '.join(batch_codes[:5])}" + (" ..." if len(batch_codes) > 5 else ""))

            # Manual skip button: touch data/skip.now to skip this batch instantly
            if skip_trigger_path.exists():
                skip_trigger_path.unlink(missing_ok=True)
                print(f"⏭️  Manual skip triggered → skipping batch {batch_num}")
                mark_skipped(skipped_registry, batch_codes, reason="manual-trigger")
                start += args.batch_size
                continue

            batch_start_time = time.time()
            
            try:
                # Run the batch with a wall-clock guard
                batch_out = await asyncio.wait_for(
                    process_batch(batch_codes, iso_tables, batch_num, skip_geo=args.skip_geo),
                    timeout=args.max_batch_seconds
                )
                
                batch_duration = time.time() - batch_start_time
                print(f"\n  ✅ Batch completed in {batch_duration:.1f}s")
                
            except asyncio.TimeoutError:
                batch_duration = time.time() - batch_start_time
                print(f"\n  ⏳ Batch {batch_num} exceeded {args.max_batch_seconds}s → skipping")
                mark_skipped(skipped_registry, batch_codes, reason="timeout")
                # Write current state and continue
                atomic_write(out_path, existing)
                save_progress(done_codes, len(target_codes))
                start += args.batch_size
                continue
                
            except Exception as e:
                batch_duration = time.time() - batch_start_time
                print(f"\n  ❌ Batch {batch_num} failed: {e}")
                # Mark skipped but keep going
                mark_skipped(skipped_registry, batch_codes, reason=f"error:{type(e).__name__}")
                atomic_write(out_path, existing)
                save_progress(done_codes, len(target_codes))
                start += args.batch_size
                continue

            # Merge into existing and write atomically
            print(f"  💾 Saving {len(batch_out)} languages...")
            with time_block("save_batch_results"):
                existing.update(batch_out)
                atomic_write(out_path, existing)

            # Update progress
            done_codes.update(batch_out.keys())
            save_progress(done_codes, len(target_codes))
            
            # Print overall progress
            print_progress_bar(len(done_codes), len(target_codes))

            start += args.batch_size
            
            # Be nice to public endpoints
            if start < len(remaining):
                print(f"\n  😴 Pausing 0.5s before next batch...")
                await asyncio.sleep(0.5)

        print(f"\n\n{'='*80}")
        print(f"✅ Build Complete!")
        print(f"{'='*80}")
        print(f"   Total records in {out_path}: {len(existing)}")
        if SKIPPED_PATH.exists():
            skipped_count = len(load_existing(SKIPPED_PATH).get("batches", []))
            print(f"   Skipped batches: {skipped_count} (see {SKIPPED_PATH})")
        print(f"{'='*80}\n")

        # Print profiling summary
        print_summary(top_n=30)
        
        # Optionally export detailed profiling
        if args.profile:
            export_profile(PROFILE_PATH)
            print(f"📊 Detailed profiling exported to {PROFILE_PATH}")

if __name__ == "__main__":
    asyncio.run(main())