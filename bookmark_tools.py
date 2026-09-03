"""Core bookmark operations used by the MCP server and API agent."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

STORE_PATH = Path(os.getenv("BOOKMARK_STORE_PATH", "bookmarks.json"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _load_bookmarks() -> list[dict[str, Any]]:
    if not STORE_PATH.exists():
        return []
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _save_bookmarks(bookmarks: list[dict[str, Any]]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = STORE_PATH.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(bookmarks, indent=2), encoding="utf-8")
    temporary_path.replace(STORE_PATH)


def _canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def _normalize(bookmark: dict[str, Any], source: str | None = None) -> dict[str, str]:
    url = str(bookmark.get("url", "")).strip()
    if not url:
        raise ValueError("Every bookmark must contain a URL.")
    return {
        "id": str(bookmark.get("id") or uuid.uuid4()),
        "title": str(bookmark.get("title") or url).strip(),
        "url": url,
        "source": source or str(bookmark.get("source") or "unknown"),
        "category": str(bookmark.get("category") or "Uncategorized"),
        "added": str(bookmark.get("added") or datetime.now(UTC).isoformat()),
    }


def _completion(instructions: str, payload: Any) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY must be configured for AI operations.")
    response = OpenAI(api_key=api_key).chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def sync_bookmarks(chrome: list[dict[str, Any]], edge: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge Chrome and Edge bookmarks, de-duplicating canonical URLs."""
    merged: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for source, bookmarks in (("chrome", chrome), ("edge", edge)):
        for bookmark in bookmarks:
            normalized = _normalize(bookmark, source)
            canonical_url = _canonical_url(normalized["url"])
            if canonical_url not in seen_urls:
                seen_urls.add(canonical_url)
                merged.append(normalized)
    _save_bookmarks(merged)
    return {"bookmarks": merged, "count": len(merged)}


def categorize_bookmarks(bookmarks: list[dict[str, Any]]) -> dict[str, Any]:
    """Assign a concise category to each bookmark using GPT."""
    normalized = [_normalize(bookmark) for bookmark in bookmarks]
    prompt = (
        "Assign one concise category to every bookmark. Return only a JSON array with "
        "objects containing id and category. Use broad reusable labels such as Work, "
        "Learning, News, Shopping, Entertainment, or Reference."
    )
    try:
        categories = json.loads(_completion(prompt, normalized))
    except json.JSONDecodeError as error:
        raise RuntimeError("AI Core returned invalid category JSON.") from error
    category_by_id = {str(item["id"]): str(item["category"]) for item in categories}
    for bookmark in normalized:
        bookmark["category"] = category_by_id.get(bookmark["id"], bookmark["category"])
    _save_bookmarks(normalized)
    return {"bookmarks": normalized, "count": len(normalized)}


def find_duplicates(bookmarks: list[dict[str, Any]]) -> dict[str, Any]:
    """Find exact and likely duplicate URLs without requiring an LLM."""
    normalized = [_normalize(bookmark) for bookmark in bookmarks]
    groups: dict[str, list[dict[str, str]]] = {}
    for bookmark in normalized:
        key = _canonical_url(bookmark["url"])
        groups.setdefault(key, []).append(bookmark)
    duplicates = [group for group in groups.values() if len(group) > 1]
    return {"duplicates": duplicates, "duplicate_groups": len(duplicates)}


def search_bookmarks(bookmarks: list[dict[str, Any]], query: str) -> dict[str, Any]:
    """Ask GPT to semantically rank the supplied bookmarks for a query."""
    normalized = [_normalize(bookmark) for bookmark in bookmarks]
    prompt = (
        "Select and rank bookmarks that best answer the user's query. Return only a JSON "
        "array of bookmark ids, ordered most relevant first. Query: " + query
    )
    try:
        ranked_ids = json.loads(_completion(prompt, normalized))
    except json.JSONDecodeError as error:
        raise RuntimeError("AI Core returned invalid search JSON.") from error
    by_id = {bookmark["id"]: bookmark for bookmark in normalized}
    results = [by_id[str(bookmark_id)] for bookmark_id in ranked_ids if str(bookmark_id) in by_id]
    return {"query": query, "results": results, "count": len(results)}


def summarize_url(url: str) -> dict[str, str]:
    """Fetch readable page text and create a short AI-generated summary."""
    response = httpx.get(url, follow_redirects=True, timeout=15, headers={"User-Agent": "BookmarkAI/1.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()[:12000]
    summary = _completion("Summarize this webpage in 3 concise bullet points.", {"url": url, "content": text})
    return {"url": url, "summary": summary}


def stored_bookmarks() -> list[dict[str, Any]]:
    """Return the current unified local store for API endpoint convenience."""
    return _load_bookmarks()
