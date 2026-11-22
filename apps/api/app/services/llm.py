import httpx
from fastapi import HTTPException

from app.core.config import settings


def _headers():
    if not settings.openai_api_key:
        raise HTTPException(
            503, "AI provider is not configured. Set OPENAI_API_KEY on the API service."
        )
    return {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        for offset in range(0, len(texts), 64):
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/embeddings",
                headers=_headers(),
                json={
                    "model": settings.openai_embedding_model,
                    "input": texts[offset : offset + 64],
                },
            )
            if response.is_error:
                raise HTTPException(502, "Embedding provider request failed")
            try:
                data = response.json()["data"]
                vectors.extend(
                    item["embedding"] for item in sorted(data, key=lambda row: row["index"])
                )
            except (KeyError, TypeError, IndexError):
                raise HTTPException(
                    502, "Embedding provider returned an invalid response"
                ) from None
    return vectors


async def choose_tools(messages: list[dict], tool_specs: list[dict]) -> tuple[list[dict], dict]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
        response = await client.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers=_headers(),
            json={
                "model": settings.openai_model,
                "messages": messages,
                "tools": tool_specs,
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "max_tokens": 512,
            },
        )
    if response.is_error:
        raise HTTPException(502, "AI provider request failed")
    try:
        result = response.json()
        return result["choices"][0]["message"].get("tool_calls", []), result.get("usage", {})
    except (KeyError, TypeError, IndexError):
        raise HTTPException(502, "AI provider returned an invalid response") from None


async def stream_answer(messages: list[dict]):
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        async with client.stream(
            "POST",
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers=_headers(),
            json={
                "model": settings.openai_model,
                "messages": messages,
                "stream": True,
                "max_tokens": settings.max_completion_tokens,
                "stream_options": {"include_usage": True},
            },
        ) as response:
            if response.is_error:
                raise HTTPException(502, "AI provider request failed")
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                import json

                try:
                    payload = json.loads(line[6:])
                    delta = payload.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield {"text": delta}
                    if payload.get("usage"):
                        yield {"usage": payload["usage"]}
                except (ValueError, IndexError, AttributeError):
                    continue
