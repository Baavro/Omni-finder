# # extractor/orchestrator.py
# import asyncio, json, time
# from pathlib import Path
# from typing import List, Dict
# from pydantic import BaseModel
# import httpx

# BATCH = 50
# CACHE = Path("cache"); CACHE.mkdir(exist_ok=True)

# def cache_get(key: str):
#     p = CACHE / f"{key}.json"
#     return json.loads(p.read_text()) if p.exists() else None

# def cache_put(key: str, data: dict):
#     (CACHE / f"{key}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

# async def fetch(client: httpx.AsyncClient, url: str, params=None, key=None):
#     if key and (hit := cache_get(key)): return hit
#     r = await client.get(url, params=params, timeout=30.0)
#     r.raise_for_status()
#     data = r.json()
#     if key: cache_put(key, data)
#     await asyncio.sleep(0.1)  # be nice to endpoints
#     return data

# async def run_batches(codes: List[str], fn, label: str) -> Dict:
#     out = {}
#     for i in range(0, len(codes), BATCH):
#         chunk = codes[i:i+BATCH]
#         out.update(await fn(chunk))
#         print(f"{label}: {i+len(chunk)}/{len(codes)}")
#     return out

# extractor/orchestrator.py
import asyncio, json
from pathlib import Path
import httpx

BATCH = 50
CACHE = Path("cache"); CACHE.mkdir(exist_ok=True)

def cache_get(key: str):
    p = CACHE / f"{key}.json"
    return json.loads(p.read_text()) if p.exists() else None

def cache_put(key: str, data: dict):
    (CACHE / f"{key}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

async def fetch(client: httpx.AsyncClient, url: str, params=None, key=None):
    if key and (hit := cache_get(key)):
        return hit
    r = await client.get(url, params=params, timeout=30.0)
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        # print response text for debugging (especially useful on 400s)
        text = getattr(r, "text", "")
        raise RuntimeError(f"{e}\n--- Response body ---\n{text[:1000]}") from e
    data = r.json()
    if key: cache_put(key, data)
    await asyncio.sleep(0.1)
    return data

async def run_batches(codes, fn, label: str):
    out = {}
    for i in range(0, len(codes), BATCH):
        chunk = codes[i:i+BATCH]
        out.update(await fn(chunk))
        print(f"{label}: {i+len(chunk)}/{len(codes)}")
    return out
