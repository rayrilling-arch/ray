#!/usr/bin/env python3
"""OpenAI-compatible HTTP bridge to Ada Core over D-Bus."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dbus_client import AdaCoreUnavailable, think
from identity import MODEL_ID

HOST = "0.0.0.0"
PORT = 8000
REQUEST_TIMEOUT_MS = 120_000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ada-core.api-bridge")

app = FastAPI(title="Ada API Bridge", version="1.0.0")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool | None = False


def _latest_user_message(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user" and message.content.strip():
            return message.content.strip()
    raise HTTPException(status_code=400, detail="No user message found in request")


@app.get("/v1/models")
def list_models() -> dict[str, Any]:
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": now,
                "owned_by": "ada-core",
            }
        ],
    }


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest) -> JSONResponse:
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming is not supported")

    user_text = _latest_user_message(request.messages)
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    try:
        answer = think(user_text, timeout_ms=REQUEST_TIMEOUT_MS)
    except AdaCoreUnavailable as exc:
        logger.error("Ada Core unavailable: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="Ada Core is unavailable") from exc
    except Exception as exc:
        logger.exception("Chat completion failed")
        raise HTTPException(status_code=500, detail="Internal bridge error") from exc

    payload = {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
    return JSONResponse(content=payload)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
