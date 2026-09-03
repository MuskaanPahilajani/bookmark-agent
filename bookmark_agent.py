"""LangGraph agent that selects BookmarkAI MCP tools through SAP AI Core."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from operator import add
from contextlib import AsyncExitStack
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI


class AgentState(TypedDict):
    messages: Annotated[list[dict[str, Any]], add]


class BookmarkAgent:
    """Maintains one MCP subprocess and compiles the three-node StateGraph."""

    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None
        self._tools: list[dict[str, Any]] = []
        self._client: OpenAI | None = None
        self.graph: Any = None

    async def start(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY must be configured.")
        self._client = OpenAI(api_key=api_key)
        parameters = StdioServerParameters(command=sys.executable, args=["mcp_server_bookmarks.py"])
        read_stream, write_stream = await self._stack.enter_async_context(stdio_client(parameters))
        self._session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
        await self._session.initialize()
        tools = await self._session.list_tools()
        self._tools = [
            {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.inputSchema}}
            for tool in tools.tools
        ]
        self.graph = self._build_graph()

    async def stop(self) -> None:
        await self._stack.aclose()

    def _build_graph(self) -> Any:
        graph = StateGraph(AgentState)
        graph.add_node("agent_node", self._agent_node)
        graph.add_node("tool_node", self._tool_node)
        graph.add_edge(START, "agent_node")
        graph.add_conditional_edges("agent_node", self._should_continue, {"tool_node": "tool_node", "end": END})
        graph.add_edge("tool_node", "agent_node")
        return graph.compile()

    async def _agent_node(self, state: AgentState) -> dict[str, list[dict[str, Any]]]:
        assert self._client is not None
        response = await asyncio.to_thread(
            self._client.chat.completions.create,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=state["messages"],
            tools=self._tools,
            tool_choice="auto",
            temperature=0,
        )
        message = response.choices[0].message
        return {"messages": [message.model_dump(exclude_none=True)]}

    @staticmethod
    def _should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        return "tool_node" if last_message.get("tool_calls") else "end"

    async def _tool_node(self, state: AgentState) -> dict[str, list[dict[str, Any]]]:
        assert self._session is not None
        last_message = state["messages"][-1]
        tool_messages: list[dict[str, Any]] = []
        for call in last_message["tool_calls"]:
            arguments = json.loads(call["function"]["arguments"])
            result = await self._session.call_tool(call["function"]["name"], arguments)
            content = "\n".join(item.text for item in result.content if hasattr(item, "text"))
            tool_messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})
        return {"messages": tool_messages}

    async def invoke(self, instruction: str) -> dict[str, Any]:
        if self.graph is None:
            raise RuntimeError("Bookmark agent has not started.")
        result = await self.graph.ainvoke(
            {"messages": [{"role": "system", "content": "You are BookmarkAI. Use the requested tool exactly once, then report its result."}, {"role": "user", "content": instruction}]}
        )
        return result
