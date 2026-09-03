"""FastAPI entry point for the BookmarkAI synchronizer agent."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from bookmark_agent import BookmarkAgent
from bookmark_tools import stored_bookmarks


class Bookmark(BaseModel):
    id: str | None = None
    title: str = ""
    url: str
    source: str | None = None
    category: str | None = None
    added: str | None = None


class SyncRequest(BaseModel):
    chrome: list[Bookmark] = Field(default_factory=list)
    edge: list[Bookmark] = Field(default_factory=list)


class BookmarksRequest(BaseModel):
    bookmarks: list[Bookmark] | None = None


class SearchRequest(BookmarksRequest):
    query: str


class SummaryRequest(BaseModel):
    url: str


agent = BookmarkAgent()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await agent.start()
    yield
    await agent.stop()


app = FastAPI(title="BookmarkAI Synchronizer", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


def as_dicts(bookmarks: list[Bookmark]) -> list[dict[str, Any]]:
    return [bookmark.model_dump(exclude_none=True) for bookmark in bookmarks]


async def invoke_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    instruction = f"Invoke the {tool_name} tool with exactly this JSON input: {json.dumps(arguments)}"
    try:
        result = await agent.invoke(instruction)
        tool_messages = [message for message in result["messages"] if message.get("role") == "tool"]
        if not tool_messages:
            raise RuntimeError("The agent did not invoke a tool.")
        return json.loads(tool_messages[-1]["content"])
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "BookmarkAI Synchronizer",
        "health": "/health",
        "docs": "/docs",
    }


@app.post("/sync")
async def sync(payload: SyncRequest) -> Any:
    return await invoke_tool("sync", {"chrome": as_dicts(payload.chrome), "edge": as_dicts(payload.edge)})


@app.post("/categorize")
async def categorize(payload: BookmarksRequest) -> Any:
    bookmarks = as_dicts(payload.bookmarks) if payload.bookmarks is not None else stored_bookmarks()
    return await invoke_tool("categorize", {"bookmarks": bookmarks})


@app.post("/search")
async def search(payload: SearchRequest) -> Any:
    bookmarks = as_dicts(payload.bookmarks) if payload.bookmarks is not None else stored_bookmarks()
    return await invoke_tool("search", {"bookmarks": bookmarks, "query": payload.query})


@app.post("/duplicates")
async def duplicates(payload: BookmarksRequest) -> Any:
    bookmarks = as_dicts(payload.bookmarks) if payload.bookmarks is not None else stored_bookmarks()
    return await invoke_tool("duplicates", {"bookmarks": bookmarks})


@app.post("/summarize")
async def summarize(payload: SummaryRequest) -> Any:
    return await invoke_tool("summarize", {"url": payload.url})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
