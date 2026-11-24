import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = "web"


@dataclass(frozen=True, slots=True)
class SearchResponse:
    results: list[SearchResult]
    query: str
    error: str | None = None


class WebSearchEngine:
    def __init__(
        self,
        *,
        command: list[str] | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._command = command or ["npx", "-y", "@modelcontextprotocol/server-brave-search"]
        self._env = env or {}
        self._timeout = timeout
        self._session: ClientSession | None = None
        self._read_stream: Any = None
        self._write_stream: Any = None
        self._stdio_context: Any = None

    @asynccontextmanager
    async def _connect(self):
        if self._session is not None:
            yield self._session
            return

        params = StdioServerParameters(
            command=self._command[0],
            args=self._command[1:],
            env={**self._env},
        )
        try:
            self._stdio_context = stdio_client(params)
            self._read_stream, self._write_stream = await self._stdio_context.__aenter__()
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.__aenter__()
            await self._session.initialize()
            log.info("MCP search server connected")
            yield self._session
        except Exception as exc:
            log.error("Failed to connect to MCP search server: %s", exc)
            raise
        finally:
            await self.close()

    async def close(self) -> None:
        if self._session is not None:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
        if self._stdio_context is not None:
            try:
                await self._stdio_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._stdio_context = None
        self._read_stream = None
        self._write_stream = None

    async def search(self, query: str, *, count: int = 10) -> SearchResponse:
        if not query.strip():
            return SearchResponse(results=[], query=query, error="empty query")

        async with self._connect() as session:
            try:
                result = await asyncio.wait_for(
                    session.call_tool("brave_web_search", {"query": query, "count": count}),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                return SearchResponse(results=[], query=query, error="search timeout")
            except Exception as exc:
                log.error("MCP search call failed: %s", exc)
                return SearchResponse(results=[], query=query, error=str(exc))

        try:
            content = result.content
            if isinstance(content, list):
                text = "".join(c.text for c in content if hasattr(c, "text"))
            else:
                text = str(content)
            data = json.loads(text)
        except (json.JSONDecodeError, AttributeError) as exc:
            log.error("Failed to parse search response: %s", exc)
            return SearchResponse(results=[], query=query, error="invalid response format")

        results = []
        for item in data.get("results", {}).get("web", [])[:count]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source="web",
                )
            )
        return SearchResponse(results=results, query=query)


async def search_web(query: str, count: int = 10) -> SearchResponse:
    engine = WebSearchEngine()
    try:
        return await engine.search(query, count=count)
    finally:
        await engine.close()