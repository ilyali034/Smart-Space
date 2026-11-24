import ollama, httpx, json

from .config import * 

def _parse_arguments(raw: Any) -> tuple[dict[str, Any], str | None]:
    if isinstance(raw, dict):
        return raw, None
    if raw in (None, ""):
        return {}, None
    if isinstance(raw, str):  # some models/versions return the arguments as a JSON string
        try:
            parsed = json.loads(raw)
        except ValueError:
            return {}, f"arguments are not valid JSON: {raw[:80]!r}"
        if isinstance(parsed, dict):
            return parsed, None
    return {}, f"arguments must be an object, got {type(raw).__name__}"

class OllamaClient:
    def __init__(self, client: httpx.AsyncClient, *, model: str, keep_alive: str = "30m",
                 temperature: float = 0.1, num_ctx: int = 4096) -> None:
        self._http = client
        self.model = model
        self._keep_alive = keep_alive
        self._options = {"temperature": temperature, "num_ctx": num_ctx}

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        on_token: Callable[[str], None] | None = None,
    ) -> ChatMessage:
        """One model turn. Streams internally so `on_token` can show/speak text as it is generated."""
        payload: dict[str, Any] = {
            "model": self.model, "messages": messages, "stream": True,
            "keep_alive": self._keep_alive, "options": self._options,
        }
        if tools:
            payload["tools"] = tools
        out = ChatMessage()
        try:
            async with self._http.stream("POST", "/api/chat", json=payload) as resp:
                if resp.status_code != 200:
                    raise self._http_error(resp.status_code, (await resp.aread()).decode("utf-8", "replace"))
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except ValueError as exc:
                        raise OllamaError(OllamaErrorKind.BAD_RESPONSE, "Ollama sent a malformed chunk") from exc
                    if "error" in chunk:
                        raise self._http_error(500, json.dumps(chunk))
                    msg = chunk.get("message") or {}
                    if token := msg.get("content"):
                        out.content += token
                        if on_token:
                            on_token(token)
                    for call in msg.get("tool_calls") or []:
                        fn = call.get("function") or {}
                        args, err = _parse_arguments(fn.get("arguments"))
                        out.tool_calls.append(ToolCall(str(fn.get("name", "")), args, err))
                    if chunk.get("done"):
                        break
        except httpx.TimeoutException as exc:
            raise OllamaError(OllamaErrorKind.TIMEOUT, "Ollama did not answer in time (is the model still loading?)") from exc
        except httpx.TransportError as exc:
            raise OllamaError(
                OllamaErrorKind.UNREACHABLE, f"Cannot reach Ollama at {self._http.base_url}. Is `ollama serve` running?"
            ) from exc
        out.content = out.content.strip()
        return out
    
    async def list_models(self) -> list[str]:
        try:
            resp = await self._http.get("/api/tags")
        except httpx.TimeoutException as exc:
            raise OllamaError(OllamaErrorKind.TIMEOUT, "Ollama did not answer in time") from exc
        except httpx.TransportError as exc:
            raise OllamaError(OllamaErrorKind.UNREACHABLE, f"Cannot reach Ollama at {self._http.base_url}") from exc
        if resp.status_code != 200:
            raise self._http_error(resp.status_code, resp.text)
        return [m["name"] for m in resp.json().get("models", [])] 

    async def check(self) -> None:
        """Fail early with a helpful message: server up and model pulled."""
        models = await self.list_models()
        wanted = self.model if ":" in self.model else f"{self.model}:latest"
        if wanted not in models:
            raise OllamaError(
                OllamaErrorKind.MODEL_NOT_FOUND,
                f"Model '{self.model}' is not installed. Run: ollama pull {self.model}  (installed: {', '.join(models) or 'none'})",
            ) 

    def _http_error(self, status: int, body: str) -> OllamaError:
        try:
            detail = str(json.loads(body).get("error", body))
        except ValueError:
            detail = body
        low = detail.lower()
        if "does not support tools" in low:
            return OllamaError(
                OllamaErrorKind.NO_TOOLS_SUPPORT,
                f"Model '{self.model}' does not support tool calling. Use e.g. qwen2.5, llama3.1 or mistral-nemo.",
            )
        if status == 404 or "not found" in low:
            return OllamaError(
                OllamaErrorKind.MODEL_NOT_FOUND, f"Model '{self.model}' not found. Run: ollama pull {self.model}"
            )
        return OllamaError(OllamaErrorKind.HTTP, f"Ollama error {status}: {detail[:200]}")
