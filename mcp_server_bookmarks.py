"""MCP stdio server exposing BookmarkAI's five tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from bookmark_tools import (
    categorize_bookmarks,
    find_duplicates,
    search_bookmarks,
    summarize_url,
    sync_bookmarks,
)

mcp = FastMCP("BookmarkAI")


@mcp.tool()
def sync(chrome: list[dict[str, Any]], edge: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge Chrome and Edge bookmark lists and persist the unified result."""
    return sync_bookmarks(chrome, edge)


@mcp.tool()
def categorize(bookmarks: list[dict[str, Any]]) -> dict[str, Any]:
    """Assign semantic category labels to bookmarks."""
    return categorize_bookmarks(bookmarks)


@mcp.tool()
def search(bookmarks: list[dict[str, Any]], query: str) -> dict[str, Any]:
    """Semantically search supplied bookmarks for a natural-language query."""
    return search_bookmarks(bookmarks, query)


@mcp.tool()
def duplicates(bookmarks: list[dict[str, Any]]) -> dict[str, Any]:
    """Find duplicate canonical URLs among bookmarks."""
    return find_duplicates(bookmarks)


@mcp.tool()
def summarize(url: str) -> dict[str, str]:
    """Fetch and summarize a webpage at a URL."""
    return summarize_url(url)


if __name__ == "__main__":
    mcp.run(transport="stdio")
