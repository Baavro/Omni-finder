# # extractor/wikidata.py
# from __future__ import annotations
# import httpx
# from typing import List, Dict
# from .orchestrator import cache_get, cache_put

# ENDPOINT = "https://query.wikidata.org/sparql"
# HEADERS = {
#     "User-Agent": "OmnilingualFinder/0.1 (https://github.com/yourname/omnilingual-finder)",
#     "Accept": "application/sparql-results+json"
# }

# def _values_block(codes: List[str]) -> str:
#     # VALUES ?iso { "awa" "bho" ... }
#     return " ".join(f'"{c}"' for c in codes)

# def sparql_for_codes(codes: List[str]) -> str:
#     values = _values_block(codes)
#     return f"""
# PREFIX wdt: <http://www.wikidata.org/prop/direct/>
# PREFIX wd: <http://www.wikidata.org/entity/>
# PREFIX schema: <http://schema.org/>

# SELECT ?iso ?lang ?autonym ?speakers ?glotto ?script ?wp WHERE {{
#   VALUES ?iso {{ {values} }}
#   ?lang wdt:P220 ?iso .
#   OPTIONAL {{ ?lang wdt:P1705 ?autonym . }}         # native label (autonym)
#   OPTIONAL {{ ?lang wdt:P1098 ?speakers . }}       # number of speakers
#   OPTIONAL {{ ?lang wdt:P1394 ?glotto . }}         # Glottolog code
#   OPTIONAL {{ ?lang wdt:P282 ?script . }}          # writing system
#   OPTIONAL {{
#     ?wpArticle schema:about ?lang ;
#                schema:isPartOf <https://en.wikipedia.org/> ;
#                schema:name ?wp .
#   }}
# }}
# """

# async def _post_sparql(client: httpx.AsyncClient, query: str) -> Dict:
#     # cache by hash of the query
#     key = f"wd_{hash(query)}"
#     if (hit := cache_get(key)):
#         return hit
#     # POST is friendlier to Wikidata than long GETs
#     r = await client.post(
#         ENDPOINT,
#         headers=HEADERS,
#         data={"query": query, "format": "json"},
#         timeout=60.0,
#     )
#     # basic retry on rate limit
#     if r.status_code in (429, 502, 503, 504):
#         await client.aclose()
#         async with httpx.AsyncClient() as retry_client:
#             r = await retry_client.post(
#                 ENDPOINT, headers=HEADERS, data={"query": query, "format": "json"}, timeout=60.0
#             )
#     r.raise_for_status()
#     data = r.json()
#     cache_put(key, data)
#     return data

# async def fetch_batch(codes: List[str]) -> Dict[str, Dict]:
#     if not codes:
#         return {}
#     query = sparql_for_codes(codes)
#     async with httpx.AsyncClient() as client:
#         data = await _post_sparql(client, query)

#     rows = data.get("results", {}).get("bindings", [])
#     out: Dict[str, Dict] = {}
#     for r in rows:
#         iso = r["iso"]["value"]
#         def _get(name):
#             return r.get(name, {}).get("value")
#         speakers_raw = _get("speakers")
#         try:
#             speakers = int(float(speakers_raw)) if speakers_raw is not None else None
#         except Exception:
#             speakers = None

#         script_value = _get("script")  # full IRI like http://www.wikidata.org/entity/Q8216
#         # Keep as-is for now; script name comes from CLDR later.

#         out[iso] = {
#             "autonym": _get("autonym"),
#             "speakers": speakers,
#             "glottocode": _get("glotto"),
#             "scripts": [script_value] if script_value else [],
#             "wikipedia": _get("wp"),
#             "_raw": r,
#         }
#     return out

# # Append to extractor/wikidata.py
# from typing import Tuple

# def _values_block(codes: List[str]) -> str:
#     return " ".join(f'"{c}"' for c in codes)

# def sparql_geo_for_codes(codes: List[str]) -> str:
#     values = _values_block(codes)
#     return f"""
# PREFIX wdt: <http://www.wikidata.org/prop/direct/>
# PREFIX wd: <http://www.wikidata.org/entity/>
# PREFIX schema: <http://schema.org/>

# SELECT ?iso ?country ?countryCode ?countryLabel ?adm1 ?adm1Label WHERE {{
#   VALUES ?iso {{ {values} }}
#   ?lang wdt:P220 ?iso .

#   # Countries: (official language) OR (language used)
#   OPTIONAL {{
#     VALUES ?p {{ wdt:P37 wdt:P2936 }}
#     ?country ?p ?lang .
#     OPTIONAL {{ ?country wdt:P297 ?countryCode . }}
#     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
#   }}

#   # Admin-1 / regions that 'use' the language
#   OPTIONAL {{
#     ?adm1 wdt:P2936 ?lang .
#     ?adm1 wdt:P31/wdt:P279* wd:Q56061 .    # administrative territorial entity
#     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
#   }}
# }}
# """

# async def fetch_geo_batch(codes: List[str]) -> Dict[str, Dict]:
#     if not codes:
#         return {}
#     query = sparql_geo_for_codes(codes)
#     async with httpx.AsyncClient() as client:
#         data = await _post_sparql(client, query)

#     rows = data.get("results", {}).get("bindings", [])
#     out: Dict[str, Dict] = {}
#     for r in rows:
#         iso = r["iso"]["value"]
#         d = out.setdefault(iso, {"countries": set(), "regions": set(), "country_codes": {}})
#         # country
#         if "countryLabel" in r:
#             label = r["countryLabel"]["value"]
#             d["countries"].add(label)
#         if "countryCode" in r and r["countryCode"].get("value"):
#             cc = r["countryCode"]["value"]  # e.g., IN
#             d["country_codes"][cc] = True
#         # admin-1
#         if "adm1Label" in r:
#             d["regions"].add(r["adm1Label"]["value"])

#     # normalize sets -> lists and prefer ISO2 if available
#     norm = {}
#     for iso, v in out.items():
#         iso2s = sorted(v["country_codes"].keys())
#         norm[iso] = {
#             "countries_iso2": iso2s,                       # authoritative if present
#             "countries_labels": sorted(v["countries"]),    # fallback display
#             "regions": sorted(v["regions"]),
#         }
#     return norm

# # extractor/wikidata.py
# from __future__ import annotations
# import asyncio
# import json
# import re
# from typing import Dict, List

# import httpx

# from .orchestrator import cache_get, cache_put

# ENDPOINT = "https://query.wikidata.org/sparql"
# HEADERS = {
#     "User-Agent": "OmnilingualFinder/0.1 (+https://github.com/yourname/omnilingual-finder)",
#     "Accept": "application/sparql-results+json",
# }

# _CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")  # control chars except \t\r\n (we keep those)


# # ---------- Query builders ----------

# def _values_block(codes: List[str]) -> str:
#     # VALUES ?iso { "awa" "bho" ... }
#     return " ".join(f'"{c}"' for c in codes)


# def sparql_for_codes(codes: List[str]) -> str:
#     values = _values_block(codes)
#     return f"""
# PREFIX wdt: <http://www.wikidata.org/prop/direct/>
# PREFIX schema: <http://schema.org/>

# SELECT ?iso ?lang ?autonym ?speakers ?glotto ?script ?wp WHERE {{
#   VALUES ?iso {{ {values} }}
#   ?lang wdt:P220 ?iso .
#   OPTIONAL {{ ?lang wdt:P1705 ?autonym . }}         # native name (autonym)
#   OPTIONAL {{ ?lang wdt:P1098 ?speakers . }}        # number of speakers
#   OPTIONAL {{ ?lang wdt:P1394 ?glotto . }}          # Glottolog code
#   OPTIONAL {{ ?lang wdt:P282 ?script . }}           # writing system
#   OPTIONAL {{
#     ?wpArticle schema:about ?lang ;
#                schema:isPartOf <https://en.wikipedia.org/> ;
#                schema:name ?wp .
#   }}
# }}
# """


# def sparql_geo_for_codes(codes: List[str]) -> str:
#     values = _values_block(codes)
#     return f"""
# PREFIX wdt: <http://www.wikidata.org/prop/direct/>
# PREFIX wd: <http://www.wikidata.org/entity/>
# PREFIX schema: <http://schema.org/>

# SELECT ?iso ?country ?countryCode ?countryLabel ?adm1 ?adm1Label WHERE {{
#   VALUES ?iso {{ {values} }}
#   ?lang wdt:P220 ?iso .

#   # Countries: official language (P37) OR language used (P2936)
#   OPTIONAL {{
#     VALUES ?p {{ wdt:P37 wdt:P2936 }}
#     ?country ?p ?lang .
#     OPTIONAL {{ ?country wdt:P297 ?countryCode . }}
#     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
#   }}

#   # Admin-1/regions that 'use' the language (P2936)
#   OPTIONAL {{
#     ?adm1 wdt:P2936 ?lang .
#     ?adm1 wdt:P31/wdt:P279* wd:Q56061 .    # administrative territorial entity
#     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
#   }}
# }}
# """


# # ---------- HTTP / parsing helpers ----------

# def _safe_json_parse(resp: httpx.Response) -> dict:
#     """
#     Parse JSON robustly:
#     - try native .json()
#     - on JSONDecodeError, strip control chars (except \t\r\n) and try again
#     - if still failing, raise with a trimmed body preview
#     """
#     ctype = resp.headers.get("Content-Type", "")
#     text = resp.text  # always available

#     try:
#         return resp.json()
#     except json.JSONDecodeError:
#         cleaned = _CONTROL_CHARS.sub(
#             lambda m: "" if m.group(0) not in ("\t", "\r", "\n") else m.group(0), text
#         )
#         try:
#             return json.loads(cleaned)
#         except json.JSONDecodeError as e2:
#             snippet = text[:1000]
#             raise RuntimeError(
#                 "SPARQL returned non-JSON or malformed JSON.\n"
#                 f"Content-Type: {ctype}\n"
#                 f"First 1000 chars:\n{snippet}"
#             ) from e2


# async def _post_sparql(query: str, *, timeout: float = 150.0, max_retries: int = 5) -> Dict:
#     """
#     POST a SPARQL query with retries (handles 429/5xx/timeouts) and robust JSON parsing.
#     Cached by the hash of the query string (only after successful parse).
#     """
#     key = f"wd_{hash(query)}"
#     hit = cache_get(key)
#     if hit:
#         return hit

#     delay = 1.0
#     for attempt in range(max_retries):
#         try:
#             async with httpx.AsyncClient(timeout=timeout) as client:
#                 r = await client.post(
#                     ENDPOINT, headers=HEADERS, data={"query": query, "format": "json"}
#                 )
#                 # retry on common server/rate-limit statuses
#                 if r.status_code in (429, 502, 503, 504):
#                     raise httpx.HTTPStatusError(
#                         f"{r.status_code} from Wikidata", request=r.request, response=r
#                     )
#                 r.raise_for_status()
#                 data = _safe_json_parse(r)
#                 cache_put(key, data)  # cache only valid JSON
#                 return data
#         except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.HTTPStatusError):
#             if attempt == max_retries - 1:
#                 raise
#             await asyncio.sleep(delay)
#             delay = min(delay * 2, 8.0)


# # ---------- Public fetchers ----------

# async def fetch_batch(
#     codes: List[str], *, timeout: float = 90.0, retries: int = 4
# ) -> Dict[str, Dict]:
#     """
#     Fetch core language info by ISO 639-3 codes.
#     Returns: dict[iso] -> {autonym, speakers, glottocode, scripts[], wikipedia, _raw}
#     """
#     if not codes:
#         return {}
#     query = sparql_for_codes(codes)
#     data = await _post_sparql(query, timeout=timeout, max_retries=retries)
#     rows = data.get("results", {}).get("bindings", [])

#     out: Dict[str, Dict] = {}
#     for r in rows:
#         iso = r["iso"]["value"]

#         def _get(name):  # helper to safely extract values
#             return r.get(name, {}).get("value")

#         speakers_raw = _get("speakers")
#         try:
#             speakers = int(float(speakers_raw)) if speakers_raw is not None else None
#         except Exception:
#             speakers = None

#         script_value = _get("script")  # full IRI (we keep it; CLDR maps later)

#         out[iso] = {
#             "autonym": _get("autonym"),
#             "speakers": speakers,
#             "glottocode": _get("glotto"),
#             "scripts": [script_value] if script_value else [],
#             "wikipedia": _get("wp"),
#             "_raw": r,
#         }
#     return out


# async def _fetch_geo_single(iso: str, *, timeout: float, retries: int) -> Dict[str, Dict]:
#     """
#     Geo fallback for a single ISO code.
#     Returns: {iso: {countries, regions, country_codes}}
#     """
#     q = sparql_geo_for_codes([iso])
#     data = await _post_sparql(q, timeout=timeout, max_retries=retries)
#     rows = data.get("results", {}).get("bindings", [])

#     out = {iso: {"countries": set(), "regions": set(), "country_codes": {}}}
#     for r in rows:
#         if "countryLabel" in r:
#             out[iso]["countries"].add(r["countryLabel"]["value"])
#         if "countryCode" in r and r["countryCode"].get("value"):
#             out[iso]["country_codes"][r["countryCode"]["value"]] = True
#         if "adm1Label" in r:
#             out[iso]["regions"].add(r["adm1Label"]["value"])
#     return out


# async def fetch_geo_batch(
#     codes: List[str],
#     *,
#     timeout: float = 150.0,   # generous: geo payloads can be big
#     retries: int = 5,
#     chunk_size: int = 6,      # small chunks reduce payload issues
#     pause_between: float = 0.8
# ) -> Dict[str, Dict]:
#     """
#     Fetch geo info in chunks. On ANY failure (timeout, HTTP, parse), fallback to per-ISO.
#     Returns dict[iso] -> {countries_iso2, countries_labels, regions}
#     """
#     result: Dict[str, Dict] = {}

#     for i in range(0, len(codes), chunk_size):
#         chunk = codes[i:i + chunk_size]
#         try:
#             q = sparql_geo_for_codes(chunk)
#             data = await _post_sparql(q, timeout=timeout, max_retries=retries)
#             rows = data.get("results", {}).get("bindings", [])

#             tmp: Dict[str, Dict] = {}
#             for r in rows:
#                 iso = r["iso"]["value"]
#                 d = tmp.setdefault(iso, {"countries": set(), "regions": set(), "country_codes": {}})
#                 if "countryLabel" in r:
#                     d["countries"].add(r["countryLabel"]["value"])
#                 if "countryCode" in r and r["countryCode"].get("value"):
#                     d["country_codes"][r["countryCode"]["value"]] = True
#                 if "adm1Label" in r:
#                     d["regions"].add(r["adm1Label"]["value"])

#             # normalize + merge
#             for iso, v in tmp.items():
#                 iso2s = sorted(v["country_codes"].keys())
#                 result[iso] = {
#                     "countries_iso2": iso2s,
#                     "countries_labels": sorted(v["countries"]),
#                     "regions": sorted(v["regions"]),
#                 }

#         except Exception:
#             # Fallback to single-ISO queries for this chunk on ANY failure
#             for iso in chunk:
#                 try:
#                     single = await _fetch_geo_single(iso, timeout=timeout, retries=retries)
#                     v = single.get(iso, {"countries": set(), "regions": set(), "country_codes": {}})
#                     iso2s = sorted(v["country_codes"].keys())
#                     result[iso] = {
#                         "countries_iso2": iso2s,
#                         "countries_labels": sorted(v["countries"]),
#                         "regions": sorted(v["regions"]),
#                     }
#                 except Exception:
#                     # leave empty; can be filled later by community overrides
#                     result.setdefault(iso, {"countries_iso2": [], "countries_labels": [], "regions": []})

#         await asyncio.sleep(pause_between)  # be nice to Wikidata

#     return result

# # extractor/wikidata.py
# from __future__ import annotations
# import asyncio
# import json
# import re
# from typing import Dict, List

# import httpx

# from .orchestrator import cache_get, cache_put
# from .profiler import time_block, checkpoint

# ENDPOINT = "https://query.wikidata.org/sparql"
# HEADERS = {
#     "User-Agent": "OmnilingualFinder/0.1 (+https://github.com/yourname/omnilingual-finder)",
#     "Accept": "application/sparql-results+json",
# }

# _CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")  # control chars except \t\r\n (we keep those)


# # ---------- Query builders ----------

# def _values_block(codes: List[str]) -> str:
#     # VALUES ?iso { "awa" "bho" ... }
#     return " ".join(f'"{c}"' for c in codes)


# def sparql_for_codes(codes: List[str]) -> str:
#     values = _values_block(codes)
#     return f"""
# PREFIX wdt: <http://www.wikidata.org/prop/direct/>
# PREFIX schema: <http://schema.org/>

# SELECT ?iso ?lang ?autonym ?speakers ?glotto ?script ?wp WHERE {{
#   VALUES ?iso {{ {values} }}
#   ?lang wdt:P220 ?iso .
#   OPTIONAL {{ ?lang wdt:P1705 ?autonym . }}         # native name (autonym)
#   OPTIONAL {{ ?lang wdt:P1098 ?speakers . }}        # number of speakers
#   OPTIONAL {{ ?lang wdt:P1394 ?glotto . }}          # Glottolog code
#   OPTIONAL {{ ?lang wdt:P282 ?script . }}           # writing system
#   OPTIONAL {{
#     ?wpArticle schema:about ?lang ;
#                schema:isPartOf <https://en.wikipedia.org/> ;
#                schema:name ?wp .
#   }}
# }}
# """


# def sparql_geo_for_codes(codes: List[str]) -> str:
#     values = _values_block(codes)
#     return f"""
# PREFIX wdt: <http://www.wikidata.org/prop/direct/>
# PREFIX wd: <http://www.wikidata.org/entity/>
# PREFIX schema: <http://schema.org/>

# SELECT ?iso ?country ?countryCode ?countryLabel ?adm1 ?adm1Label WHERE {{
#   VALUES ?iso {{ {values} }}
#   ?lang wdt:P220 ?iso .

#   # Countries: official language (P37) OR language used (P2936)
#   OPTIONAL {{
#     VALUES ?p {{ wdt:P37 wdt:P2936 }}
#     ?country ?p ?lang .
#     OPTIONAL {{ ?country wdt:P297 ?countryCode . }}
#     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
#   }}

#   # Admin-1/regions that 'use' the language (P2936)
#   OPTIONAL {{
#     ?adm1 wdt:P2936 ?lang .
#     ?adm1 wdt:P31/wdt:P279* wd:Q56061 .    # administrative territorial entity
#     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
#   }}
# }}
# """


# # ---------- HTTP / parsing helpers ----------

# def _safe_json_parse(resp: httpx.Response) -> dict:
#     """
#     Parse JSON robustly:
#     - try native .json()
#     - on JSONDecodeError, strip control chars (except \t\r\n) and try again
#     - if still failing, raise with a trimmed body preview
#     """
#     with time_block("json_parse"):
#         ctype = resp.headers.get("Content-Type", "")
#         text = resp.text  # always available

#         try:
#             return resp.json()
#         except json.JSONDecodeError:
#             cleaned = _CONTROL_CHARS.sub(
#                 lambda m: "" if m.group(0) not in ("\t", "\r", "\n") else m.group(0), text
#             )
#             try:
#                 return json.loads(cleaned)
#             except json.JSONDecodeError as e2:
#                 snippet = text[:1000]
#                 raise RuntimeError(
#                     "SPARQL returned non-JSON or malformed JSON.\n"
#                     f"Content-Type: {ctype}\n"
#                     f"First 1000 chars:\n{snippet}"
#                 ) from e2


# async def _post_sparql(query: str, *, timeout: float = 150.0, max_retries: int = 5) -> Dict:
#     """
#     POST a SPARQL query with retries (handles 429/5xx/timeouts) and robust JSON parsing.
#     Cached by the hash of the query string (only after successful parse).
#     """
#     with time_block("wikidata_query", query_hash=hash(query), timeout=timeout):
#         key = f"wd_{hash(query)}"
        
#         # Check cache first
#         with time_block("cache_check"):
#             hit = cache_get(key)
#             if hit:
#                 checkpoint("cache_hit", key=key[:20])
#                 return hit

#         delay = 1.0
#         for attempt in range(max_retries):
#             try:
#                 with time_block(f"http_request_attempt_{attempt+1}"):
#                     async with httpx.AsyncClient(timeout=timeout) as client:
#                         r = await client.post(
#                             ENDPOINT, headers=HEADERS, data={"query": query, "format": "json"}
#                         )
                        
#                         # retry on common server/rate-limit statuses
#                         if r.status_code in (429, 502, 503, 504):
#                             checkpoint("retry_needed", status=r.status_code, attempt=attempt+1)
#                             raise httpx.HTTPStatusError(
#                                 f"{r.status_code} from Wikidata", request=r.request, response=r
#                             )
                        
#                         r.raise_for_status()
#                         data = _safe_json_parse(r)
                        
#                         with time_block("cache_write"):
#                             cache_put(key, data)  # cache only valid JSON
                        
#                         return data
                        
#             except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.HTTPStatusError) as e:
#                 if attempt == max_retries - 1:
#                     checkpoint("max_retries_exceeded", error=str(e)[:100])
#                     raise
                
#                 checkpoint("retry_wait", delay=delay, attempt=attempt+1)
#                 await asyncio.sleep(delay)
#                 delay = min(delay * 2, 8.0)


# # ---------- Public fetchers ----------

# async def fetch_batch(
#     codes: List[str], *, timeout: float = 90.0, retries: int = 4
# ) -> Dict[str, Dict]:
#     """
#     Fetch core language info by ISO 639-3 codes.
#     Returns: dict[iso] -> {autonym, speakers, glottocode, scripts[], wikipedia, _raw}
#     """
#     with time_block("wikidata_fetch_batch", num_codes=len(codes), timeout=timeout):
#         if not codes:
#             return {}
        
#         with time_block("build_query"):
#             query = sparql_for_codes(codes)
        
#         with time_block("execute_query"):
#             data = await _post_sparql(query, timeout=timeout, max_retries=retries)
        
#         with time_block("parse_results"):
#             rows = data.get("results", {}).get("bindings", [])
#             checkpoint("wikidata_results", num_rows=len(rows), num_codes=len(codes))

#             out: Dict[str, Dict] = {}
#             for r in rows:
#                 iso = r["iso"]["value"]

#                 def _get(name):  # helper to safely extract values
#                     return r.get(name, {}).get("value")

#                 speakers_raw = _get("speakers")
#                 try:
#                     speakers = int(float(speakers_raw)) if speakers_raw is not None else None
#                 except Exception:
#                     speakers = None

#                 script_value = _get("script")  # full IRI (we keep it; CLDR maps later)

#                 out[iso] = {
#                     "autonym": _get("autonym"),
#                     "speakers": speakers,
#                     "glottocode": _get("glotto"),
#                     "scripts": [script_value] if script_value else [],
#                     "wikipedia": _get("wp"),
#                     "_raw": r,
#                 }
            
#             return out


# async def _fetch_geo_single(iso: str, *, timeout: float, retries: int) -> Dict[str, Dict]:
#     """
#     Geo fallback for a single ISO code.
#     Returns: {iso: {countries, regions, country_codes}}
#     """
#     with time_block("wikidata_geo_single", iso=iso):
#         q = sparql_geo_for_codes([iso])
#         data = await _post_sparql(q, timeout=timeout, max_retries=retries)
#         rows = data.get("results", {}).get("bindings", [])

#         out = {iso: {"countries": set(), "regions": set(), "country_codes": {}}}
#         for r in rows:
#             if "countryLabel" in r:
#                 out[iso]["countries"].add(r["countryLabel"]["value"])
#             if "countryCode" in r and r["countryCode"].get("value"):
#                 out[iso]["country_codes"][r["countryCode"]["value"]] = True
#             if "adm1Label" in r:
#                 out[iso]["regions"].add(r["adm1Label"]["value"])
#         return out


# async def fetch_geo_batch(
#     codes: List[str],
#     *,
#     timeout: float = 150.0,   # generous: geo payloads can be big
#     retries: int = 5,
#     chunk_size: int = 6,      # small chunks reduce payload issues
#     pause_between: float = 0.8
# ) -> Dict[str, Dict]:
#     """
#     Fetch geo info in chunks. On ANY failure (timeout, HTTP, parse), fallback to per-ISO.
#     Returns dict[iso] -> {countries_iso2, countries_labels, regions}
#     """
#     with time_block("wikidata_geo_batch", num_codes=len(codes), chunk_size=chunk_size):
#         result: Dict[str, Dict] = {}
#         num_chunks = (len(codes) + chunk_size - 1) // chunk_size
        
#         checkpoint("geo_batch_start", num_codes=len(codes), num_chunks=num_chunks)

#         for i in range(0, len(codes), chunk_size):
#             chunk = codes[i:i + chunk_size]
#             chunk_num = i // chunk_size + 1
            
#             with time_block(f"geo_chunk_{chunk_num}", chunk_size=len(chunk)):
#                 try:
#                     with time_block("build_geo_query"):
#                         q = sparql_geo_for_codes(chunk)
                    
#                     with time_block("execute_geo_query"):
#                         data = await _post_sparql(q, timeout=timeout, max_retries=retries)
                    
#                     with time_block("parse_geo_results"):
#                         rows = data.get("results", {}).get("bindings", [])

#                         tmp: Dict[str, Dict] = {}
#                         for r in rows:
#                             iso = r["iso"]["value"]
#                             d = tmp.setdefault(iso, {"countries": set(), "regions": set(), "country_codes": {}})
#                             if "countryLabel" in r:
#                                 d["countries"].add(r["countryLabel"]["value"])
#                             if "countryCode" in r and r["countryCode"].get("value"):
#                                 d["country_codes"][r["countryCode"]["value"]] = True
#                             if "adm1Label" in r:
#                                 d["regions"].add(r["adm1Label"]["value"])

#                         # normalize + merge
#                         for iso, v in tmp.items():
#                             iso2s = sorted(v["country_codes"].keys())
#                             result[iso] = {
#                                 "countries_iso2": iso2s,
#                                 "countries_labels": sorted(v["countries"]),
#                                 "regions": sorted(v["regions"]),
#                             }
                    
#                     checkpoint("geo_chunk_success", chunk_num=chunk_num, codes_in_chunk=len(chunk))

#                 except Exception as e:
#                     # Fallback to single-ISO queries for this chunk on ANY failure
#                     checkpoint("geo_chunk_failed", chunk_num=chunk_num, error=str(e)[:100], fallback_to_single=True)
                    
#                     with time_block("geo_fallback_to_single", chunk_size=len(chunk)):
#                         for iso in chunk:
#                             try:
#                                 single = await _fetch_geo_single(iso, timeout=timeout, retries=retries)
#                                 v = single.get(iso, {"countries": set(), "regions": set(), "country_codes": {}})
#                                 iso2s = sorted(v["country_codes"].keys())
#                                 result[iso] = {
#                                     "countries_iso2": iso2s,
#                                     "countries_labels": sorted(v["countries"]),
#                                     "regions": sorted(v["regions"]),
#                                 }
#                             except Exception:
#                                 # leave empty; can be filled later by community overrides
#                                 result.setdefault(iso, {"countries_iso2": [], "countries_labels": [], "regions": []})

#                 await asyncio.sleep(pause_between)  # be nice to Wikidata

#         checkpoint("geo_batch_complete", total_codes=len(result))
#         return result

# extractor/wikidata.py
from __future__ import annotations
import asyncio
import json
import re
from typing import Dict, List

import httpx

from .orchestrator import cache_get, cache_put
from .profiler import time_block, checkpoint

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "OmnilingualFinder/0.1 (+https://github.com/yourname/omnilingual-finder)",
    "Accept": "application/sparql-results+json",
}

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")  # control chars except \t\r\n (we keep those)


# ---------- Query builders ----------

def _values_block(codes: List[str]) -> str:
    # VALUES ?iso { "awa" "bho" ... }
    return " ".join(f'"{c}"' for c in codes)


def sparql_for_codes(codes: List[str]) -> str:
    values = _values_block(codes)
    return f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>

SELECT ?iso ?lang ?autonym ?speakers ?glotto ?script ?wp WHERE {{
  VALUES ?iso {{ {values} }}
  ?lang wdt:P220 ?iso .
  OPTIONAL {{ ?lang wdt:P1705 ?autonym . }}         # native name (autonym)
  OPTIONAL {{ ?lang wdt:P1098 ?speakers . }}        # number of speakers
  OPTIONAL {{ ?lang wdt:P1394 ?glotto . }}          # Glottolog code
  OPTIONAL {{ ?lang wdt:P282 ?script . }}           # writing system
  OPTIONAL {{
    ?wpArticle schema:about ?lang ;
               schema:isPartOf <https://en.wikipedia.org/> ;
               schema:name ?wp .
  }}
}}
"""


def sparql_geo_for_codes(codes: List[str]) -> str:
    values = _values_block(codes)
    return f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX schema: <http://schema.org/>

SELECT ?iso ?country ?countryCode ?countryLabel ?adm1 ?adm1Label WHERE {{
  VALUES ?iso {{ {values} }}
  ?lang wdt:P220 ?iso .

  # Countries: official language (P37) OR language used (P2936)
  OPTIONAL {{
    VALUES ?p {{ wdt:P37 wdt:P2936 }}
    ?country ?p ?lang .
    OPTIONAL {{ ?country wdt:P297 ?countryCode . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  }}

  # Admin-1/regions that 'use' the language (P2936)
  OPTIONAL {{
    ?adm1 wdt:P2936 ?lang .
    ?adm1 wdt:P31/wdt:P279* wd:Q56061 .    # administrative territorial entity
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  }}
}}
"""


# ---------- HTTP / parsing helpers ----------

def _safe_json_parse(resp: httpx.Response) -> dict:
    """
    Parse JSON robustly:
    - try native .json()
    - on JSONDecodeError, strip control chars (except \t\r\n) and try again
    - if still failing, raise with a trimmed body preview
    """
    with time_block("json_parse"):
        ctype = resp.headers.get("Content-Type", "")
        text = resp.text  # always available

        try:
            return resp.json()
        except json.JSONDecodeError:
            cleaned = _CONTROL_CHARS.sub(
                lambda m: "" if m.group(0) not in ("\t", "\r", "\n") else m.group(0), text
            )
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e2:
                snippet = text[:1000]
                raise RuntimeError(
                    "SPARQL returned non-JSON or malformed JSON.\n"
                    f"Content-Type: {ctype}\n"
                    f"First 1000 chars:\n{snippet}"
                ) from e2


async def _post_sparql(query: str, *, timeout: float = 150.0, max_retries: int = 5) -> Dict:
    """
    POST a SPARQL query with retries (handles 429/5xx/timeouts) and robust JSON parsing.
    Cached by the hash of the query string (only after successful parse).
    """
    with time_block("wikidata_query", query_hash=hash(query), timeout=timeout, query_length=len(query)):
        key = f"wd_{hash(query)}"
        
        # Check cache first
        with time_block("cache_check"):
            hit = cache_get(key)
            if hit:
                checkpoint("cache_hit", key=key[:20])
                return hit

        # Debug: Show query size
        query_lines = len(query.strip().split('\n'))
        query_size_kb = len(query.encode('utf-8')) / 1024
        print(f"  🔍 Query: {query_lines} lines, {query_size_kb:.1f} KB")

        delay = 1.0
        for attempt in range(max_retries):
            try:
                attempt_timeout = timeout * (1 + attempt * 0.5)  # Increase timeout on retries
                print(f"  🔄 Attempt {attempt+1}/{max_retries} (timeout: {attempt_timeout:.0f}s)...")
                
                with time_block(f"http_request_attempt_{attempt+1}", timeout=attempt_timeout):
                    async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                        r = await client.post(
                            ENDPOINT, headers=HEADERS, data={"query": query, "format": "json"}
                        )
                        
                        print(f"  ✓ Response: {r.status_code} ({len(r.content)} bytes)")
                        
                        # retry on common server/rate-limit statuses
                        if r.status_code in (429, 502, 503, 504):
                            checkpoint("retry_needed", status=r.status_code, attempt=attempt+1)
                            print(f"  ⚠️  Server error {r.status_code}, retrying...")
                            raise httpx.HTTPStatusError(
                                f"{r.status_code} from Wikidata", request=r.request, response=r
                            )
                        
                        r.raise_for_status()
                        data = _safe_json_parse(r)
                        
                        # Show results
                        num_results = len(data.get("results", {}).get("bindings", []))
                        print(f"  ✅ Got {num_results} results")
                        
                        with time_block("cache_write"):
                            cache_put(key, data)  # cache only valid JSON
                        
                        return data
                        
            except httpx.TimeoutException as e:
                print(f"  ⏰ Timeout after {attempt_timeout:.0f}s")
                if attempt == max_retries - 1:
                    checkpoint("max_retries_exceeded", error="timeout")
                    print(f"  ❌ Max retries exceeded - giving up")
                    raise
                
                checkpoint("retry_wait", delay=delay, attempt=attempt+1, reason="timeout")
                print(f"  😴 Waiting {delay:.1f}s before retry...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 8.0)
                
            except (httpx.ConnectTimeout, httpx.HTTPStatusError) as e:
                print(f"  ⚠️  Error: {type(e).__name__} - {str(e)[:100]}")
                if attempt == max_retries - 1:
                    checkpoint("max_retries_exceeded", error=str(e)[:100])
                    print(f"  ❌ Max retries exceeded - giving up")
                    raise
                
                checkpoint("retry_wait", delay=delay, attempt=attempt+1, reason=type(e).__name__)
                print(f"  😴 Waiting {delay:.1f}s before retry...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 8.0)


# ---------- Public fetchers ----------

async def fetch_batch(
    codes: List[str], *, timeout: float = 90.0, retries: int = 4
) -> Dict[str, Dict]:
    """
    Fetch core language info by ISO 639-3 codes.
    Returns: dict[iso] -> {autonym, speakers, glottocode, scripts[], wikipedia, _raw}
    """
    with time_block("wikidata_fetch_batch", num_codes=len(codes), timeout=timeout):
        if not codes:
            return {}
        
        with time_block("build_query"):
            query = sparql_for_codes(codes)
        
        with time_block("execute_query"):
            data = await _post_sparql(query, timeout=timeout, max_retries=retries)
        
        with time_block("parse_results"):
            rows = data.get("results", {}).get("bindings", [])
            checkpoint("wikidata_results", num_rows=len(rows), num_codes=len(codes))

            out: Dict[str, Dict] = {}
            for r in rows:
                iso = r["iso"]["value"]

                def _get(name):  # helper to safely extract values
                    return r.get(name, {}).get("value")

                speakers_raw = _get("speakers")
                try:
                    speakers = int(float(speakers_raw)) if speakers_raw is not None else None
                except Exception:
                    speakers = None

                script_value = _get("script")  # full IRI (we keep it; CLDR maps later)

                out[iso] = {
                    "autonym": _get("autonym"),
                    "speakers": speakers,
                    "glottocode": _get("glotto"),
                    "scripts": [script_value] if script_value else [],
                    "wikipedia": _get("wp"),
                    "_raw": r,
                }
            
            return out


async def _fetch_geo_single(iso: str, *, timeout: float, retries: int) -> Dict[str, Dict]:
    """
    Geo fallback for a single ISO code.
    Returns: {iso: {countries, regions, country_codes}}
    """
    with time_block("wikidata_geo_single", iso=iso):
        q = sparql_geo_for_codes([iso])
        data = await _post_sparql(q, timeout=timeout, max_retries=retries)
        rows = data.get("results", {}).get("bindings", [])

        out = {iso: {"countries": set(), "regions": set(), "country_codes": {}}}
        for r in rows:
            if "countryLabel" in r:
                out[iso]["countries"].add(r["countryLabel"]["value"])
            if "countryCode" in r and r["countryCode"].get("value"):
                out[iso]["country_codes"][r["countryCode"]["value"]] = True
            if "adm1Label" in r:
                out[iso]["regions"].add(r["adm1Label"]["value"])
        return out


async def fetch_geo_batch(
    codes: List[str],
    *,
    timeout: float = 150.0,   # generous: geo payloads can be big
    retries: int = 5,
    chunk_size: int = 6,      # small chunks reduce payload issues
    pause_between: float = 0.8,
    use_simple_query: bool = False  # NEW: simplified query for problematic cases
) -> Dict[str, Dict]:
    """
    Fetch geo info in chunks. On ANY failure (timeout, HTTP, parse), fallback to per-ISO.
    Returns dict[iso] -> {countries_iso2, countries_labels, regions}
    """
    with time_block("wikidata_geo_batch", num_codes=len(codes), chunk_size=chunk_size):
        result: Dict[str, Dict] = {}
        num_chunks = (len(codes) + chunk_size - 1) // chunk_size
        
        checkpoint("geo_batch_start", num_codes=len(codes), num_chunks=num_chunks)

        for i in range(0, len(codes), chunk_size):
            chunk = codes[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            
            with time_block(f"geo_chunk_{chunk_num}", chunk_size=len(chunk)):
                # Try with shorter timeout first
                chunk_timeout = min(timeout, 90.0)  # Cap at 90s for chunk queries
                
                try:
                    with time_block("build_geo_query"):
                        if use_simple_query:
                            # Simplified query - just countries, no regions
                            print(f"  📍 Using simplified geo query (countries only)")
                            q = _sparql_geo_simple(chunk)
                        else:
                            q = sparql_geo_for_codes(chunk)
                    
                    with time_block("execute_geo_query"):
                        data = await _post_sparql(q, timeout=chunk_timeout, max_retries=3)  # Fewer retries for chunks
                    
                    with time_block("parse_geo_results"):
                        rows = data.get("results", {}).get("bindings", [])

                        tmp: Dict[str, Dict] = {}
                        for r in rows:
                            iso = r["iso"]["value"]
                            d = tmp.setdefault(iso, {"countries": set(), "regions": set(), "country_codes": {}})
                            if "countryLabel" in r:
                                d["countries"].add(r["countryLabel"]["value"])
                            if "countryCode" in r and r["countryCode"].get("value"):
                                d["country_codes"][r["countryCode"]["value"]] = True
                            if "adm1Label" in r:
                                d["regions"].add(r["adm1Label"]["value"])

                        # normalize + merge
                        for iso, v in tmp.items():
                            iso2s = sorted(v["country_codes"].keys())
                            result[iso] = {
                                "countries_iso2": iso2s,
                                "countries_labels": sorted(v["countries"]),
                                "regions": sorted(v["regions"]),
                            }
                    
                    checkpoint("geo_chunk_success", chunk_num=chunk_num, codes_in_chunk=len(chunk))

                except Exception as e:
                    # Fallback to single-ISO queries for this chunk on ANY failure
                    error_type = type(e).__name__
                    checkpoint("geo_chunk_failed", chunk_num=chunk_num, error=error_type, fallback_to_single=True)
                    print(f"  ⚠️  Chunk {chunk_num} failed ({error_type}), trying individual queries...")
                    
                    with time_block("geo_fallback_to_single", chunk_size=len(chunk)):
                        for j, iso in enumerate(chunk, 1):
                            try:
                                print(f"    📍 {j}/{len(chunk)}: {iso}", end=" ")
                                single = await _fetch_geo_single(iso, timeout=60.0, retries=2)  # Shorter timeout for singles
                                v = single.get(iso, {"countries": set(), "regions": set(), "country_codes": {}})
                                iso2s = sorted(v["country_codes"].keys())
                                result[iso] = {
                                    "countries_iso2": iso2s,
                                    "countries_labels": sorted(v["countries"]),
                                    "regions": sorted(v["regions"]),
                                }
                                print("✓")
                            except Exception as e2:
                                # Leave empty; can be filled later by community overrides
                                print(f"✗ ({type(e2).__name__})")
                                result.setdefault(iso, {"countries_iso2": [], "countries_labels": [], "regions": []})

                await asyncio.sleep(pause_between)  # be nice to Wikidata

        checkpoint("geo_batch_complete", total_codes=len(result))
        return result


def _sparql_geo_simple(codes: List[str]) -> str:
    """Simplified geo query - just countries, no regions (faster)"""
    values = _values_block(codes)
    return f"""
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>

SELECT ?iso ?countryCode ?countryLabel WHERE {{
  VALUES ?iso {{ {values} }}
  ?lang wdt:P220 ?iso .
  
  # Countries only (official language P37)
  OPTIONAL {{
    ?country wdt:P37 ?lang .
    OPTIONAL {{ ?country wdt:P297 ?countryCode . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  }}
}}
"""