"""Shared fixtures: a local web server for the app, and a fake Claude API.

The tests never call the real API and never need an API key: every request to
api.anthropic.com is intercepted and answered with a recorded streaming response.
"""

import functools
import http.server
import json
import socket
import threading
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent
KEY_STORAGE = "anthropic_key"
CHATS_STORAGE = "study_helper_chats"

# What the fake assistant "says": a heading, a sentence and a code block, so the
# tests can check that the Markdown renderer turns them into real HTML.
FAKE_ANSWER = "## ما هو الـ pointer؟\n\nالمؤشر هو متغير يخزّن **عنوان** متغير آخر.\n\n```c\nint x = 5;\nint *p = &x;\n```"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def app_url() -> str:
    """Serve the app over http:// (browser storage is disabled on file:// pages)."""
    port = _free_port()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(APP_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}/index.html"
    server.shutdown()


def _sse(*events: tuple[str, dict]) -> str:
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events)


def _stream_body(text: str) -> str:
    return _sse(
        ("message_start", {"type": "message_start", "message": {
            "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5",
            "content": [], "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1}}}),
        ("content_block_start", {"type": "content_block_start", "index": 0,
                                 "content_block": {"type": "text", "text": ""}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                 "delta": {"type": "text_delta", "text": text}}),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta",
                           "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                           "usage": {"output_tokens": 20}}),
        ("message_stop", {"type": "message_stop"}),
    )


CORS = {
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "*",
    "access-control-expose-headers": "*",
}


def fake_claude(page, *, status: int = 200, text: str = FAKE_ANSWER, error: dict | None = None):
    """Intercept the Claude API. 200 -> a streamed answer, anything else -> an API error."""
    def handler(route, request):
        if request.method == "OPTIONS":                       # CORS preflight
            return route.fulfill(status=204, headers=CORS)
        if status == 200:
            return route.fulfill(status=200, headers={**CORS, "content-type": "text/event-stream"},
                                 body=_stream_body(text))
        body = json.dumps(error or {"type": "error", "error": {"type": "authentication_error",
                                                               "message": "invalid x-api-key"}})
        return route.fulfill(status=status, headers={**CORS, "content-type": "application/json"},
                             body=body)

    page.route("**/v1/messages*", handler)


@pytest.fixture
def app(page, app_url):
    """An open app with an API key already saved, so tests start from a usable state."""
    page.add_init_script(f"localStorage.setItem('{KEY_STORAGE}', 'sk-ant-test-key');")
    page.goto(app_url)
    return page


@pytest.fixture
def app_without_key(page, app_url):
    page.goto(app_url)
    return page
