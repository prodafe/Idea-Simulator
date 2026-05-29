"""Research Agent — 互联网数据收集"""

import concurrent.futures
import logging
import time
from typing import Any

from config import Config

logger = logging.getLogger(__name__)

# 搜索引擎列表（按优先级）
SEARCH_ENGINES: list[dict[str, Any]] = []

# DuckDuckGo
try:
    from duckduckgo_search import DDGS

    def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r["title"], "body": r["body"][:300], "url": r.get("href", ""), "source": "web"})
        return results

    SEARCH_ENGINES.append({"name": "DuckDuckGo", "func": _ddg_search})
except ImportError:
    pass

# Wikipedia
try:
    import urllib.parse
    import urllib.request
    import json as _json

    def _wiki_search(query: str, max_results: int = 3) -> list[dict]:
        results = []
        for lang in ["zh", "en"]:
            try:
                url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
                req = urllib.request.Request(url, headers={"User-Agent": "IdeaSimulator/1.0", "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = _json.loads(resp.read())
                    if data.get("extract"):
                        results.append({"title": data.get("title", query), "body": data["extract"][:500], "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""), "source": "wikipedia"})
                        break
            except Exception:
                continue
        return results[:max_results]

    SEARCH_ENGINES.append({"name": "Wikipedia", "func": _wiki_search})
except Exception:
    pass


def multi_source_search(query: str, max_results: int = 8) -> list[dict]:
    """多数据源并行搜索"""
    all_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(SEARCH_ENGINES)) as executor:
        futures = {}
        for engine in SEARCH_ENGINES:
            n = min(max_results // len(SEARCH_ENGINES) or 1, 5)
            futures[executor.submit(engine["func"], query, n)] = engine["name"]

        for future in concurrent.futures.as_completed(futures, timeout=Config.SEARCH_TIMEOUT):
            name = futures[future]
            try:
                results = future.result()
                for r in results:
                    r["engine"] = name
                all_results.extend(results)
            except Exception as e:
                logger.debug(f"Search engine {name} failed: {e}")

    # 去重
    seen = set()
    unique = []
    for r in all_results:
        key = r.get("url", r.get("title", ""))
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique[:max_results]


def research_variable(variable: dict, idea_context: str = "") -> dict:
    """研究单个变量，搜索相关数据并分析"""
    name = variable.get("name", "")
    vtype = variable.get("type", "boolean")
    values = variable.get("values", [])

    queries = [
        f"{idea_context} {name} 现状 数据 统计",
        f"{idea_context} {name} market size trends",
        f"{name} statistics data 2025 2026",
    ]

    all_results = []
    for q in queries[:2]:
        results = multi_source_search(q, max_results=5)
        all_results.extend(results)
        time.sleep(0.3)

    # 去重
    seen = set()
    unique = []
    for r in all_results:
        k = r.get("url", "")
        if k not in seen:
            seen.add(k)
            unique.append(r)

    return {
        "variable": name,
        "type": vtype,
        "possible_values": values,
        "evidence": unique[:Config.MAX_SEARCH_RESULTS],
        "evidence_count": len(unique),
    }
