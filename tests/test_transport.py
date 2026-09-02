from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

import httpx2
import pytest

from qntx.openai._transport import (
    RECOVERY_KEY,
    RETRY_KEY,
    PaymentError,
    X402Httpx2AsyncTransport,
    X402Httpx2SyncTransport,
)


class StubHttp:
    def __init__(
        self,
        *,
        hook_headers: dict[str, str] | None = None,
        recovered: bool = False,
        fail: bool = False,
        payment_error: bool = False,
    ) -> None:
        self.hook_headers = hook_headers
        self.recovered = recovered
        self.fail = fail
        self.payment_error = payment_error
        self.create_calls = 0
        self.process_calls = 0
        self.urls: list[str] = []

    def get_payment_required_response(self, get_header: Any, body: object) -> object:
        return {"required": True, "body": body}

    def handle_payment_required(
        self, payment_required: object, request_url: str
    ) -> dict[str, str] | None:
        self.urls.append(request_url)
        return self.hook_headers

    def create_payment_payload(self, payment_required: object) -> dict[str, str]:
        self.create_calls += 1
        if self.payment_error:
            raise PaymentError("already a payment error")
        if self.fail:
            raise RuntimeError("signing failed")
        return {"stub": "payload"}

    def encode_payment_signature_header(self, payload: object) -> dict[str, str]:
        return {"PAYMENT-SIGNATURE": "signed"}

    def process_payment_result(
        self, payload: object, get_header: Any, status: int
    ) -> SimpleNamespace:
        self.process_calls += 1
        recovered = self.recovered and self.process_calls == 1
        return SimpleNamespace(recovered=recovered)


class AsyncStubHttp(StubHttp):
    async def handle_payment_required(  # type: ignore[override]
        self, payment_required: object, request_url: str
    ) -> dict[str, str] | None:
        return super().handle_payment_required(payment_required, request_url)

    async def create_payment_payload(  # type: ignore[override]
        self, payment_required: object
    ) -> dict[str, str]:
        return super().create_payment_payload(payment_required)

    async def process_payment_result(  # type: ignore[override]
        self, payload: object, get_header: Any, status: int
    ) -> SimpleNamespace:
        return super().process_payment_result(payload, get_header, status)


class CloseTrackingTransport(httpx2.BaseTransport):
    def __init__(self) -> None:
        self.closed = False

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"ok")

    def close(self) -> None:
        self.closed = True


class CloseTrackingAsyncTransport(httpx2.AsyncBaseTransport):
    def __init__(self) -> None:
        self.closed = False

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"ok")

    async def aclose(self) -> None:
        self.closed = True


class RecordingAsyncTransport(httpx2.AsyncBaseTransport):
    def __init__(self, handler: Any) -> None:
        self.handler = handler

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        return await self.handler(request)


def _iter_json() -> Iterator[bytes]:
    yield b'{"prompt":'
    yield b'"hi"}'


def test_sync_402_then_200_with_mock_transport() -> None:
    http = StubHttp()
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx2.Response(402, content=b"{}", request=request)
        assert request.headers["PAYMENT-SIGNATURE"] == "signed"
        return httpx2.Response(200, content=b"ok", request=request)

    inner = httpx2.MockTransport(handler)
    transport = X402Httpx2SyncTransport(lambda: http, inner=inner)
    response = transport.handle_request(
        httpx2.Request("POST", "https://example.com/v1/chat", content=b'{"prompt":"hi"}')
    )
    assert response.status_code == 200
    assert response.read() == b"ok"
    assert http.create_calls == 1
    assert calls["n"] == 2


def test_sync_replays_streaming_request_body() -> None:
    http = StubHttp()
    bodies: list[bytes] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(request.content)
        if len(bodies) == 1:
            return httpx2.Response(402, content=b"{}", request=request)
        return httpx2.Response(200, content=b"ok", request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    response = transport.handle_request(
        httpx2.Request("POST", "https://example.com/v1/chat", content=_iter_json())
    )
    assert response.status_code == 200
    assert bodies == [b'{"prompt":"hi"}', b'{"prompt":"hi"}']


def test_sync_non_402_passthrough() -> None:
    http = StubHttp()
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(200, content=b"ok", request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    response = transport.handle_request(httpx2.Request("GET", "https://example.com/v1/models"))
    assert response.status_code == 200
    assert calls["n"] == 1
    assert http.create_calls == 0


def test_sync_fail_closed_on_signer_error() -> None:
    http = StubHttp(fail=True)

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(402, content=b"{}", request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    with pytest.raises(PaymentError, match="Failed to handle payment"):
        transport.handle_request(httpx2.Request("GET", "https://example.com/v1/models"))


def test_sync_payment_error_not_wrapped() -> None:
    http = StubHttp(payment_error=True)

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(402, content=b"{}", request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    with pytest.raises(PaymentError, match="already a payment error"):
        transport.handle_request(httpx2.Request("GET", "https://example.com/v1/models"))


def test_sync_no_retry_loop_on_already_paid_402() -> None:
    http = StubHttp()
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(402, content=b"{}", request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    request = httpx2.Request(
        "GET",
        "https://example.com/v1/models",
        extensions={RETRY_KEY: True},
    )
    response = transport.handle_request(request)
    assert response.status_code == 402
    assert calls["n"] == 1
    assert http.create_calls == 0


def test_sync_recovery_if_process_payment_result_recovered() -> None:
    http = StubHttp(recovered=True)
    statuses: list[int] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if not statuses:
            statuses.append(402)
            return httpx2.Response(402, content=b"{}", request=request)
        if RETRY_KEY in request.extensions:
            statuses.append(200)
            return httpx2.Response(200, content=b"paid", request=request)
        statuses.append(200)
        return httpx2.Response(200, content=b"recovered", request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    response = transport.handle_request(httpx2.Request("GET", "https://example.com/v1/models"))
    assert response.read() == b"recovered"
    assert http.create_calls == 2
    assert http.process_calls == 2


def test_sync_hook_header_retry_non_402_skips_signing() -> None:
    http = StubHttp(hook_headers={"Authorization": "Bearer x"})
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx2.Response(402, content=b"{}", request=request)
        assert request.headers["Authorization"] == "Bearer x"
        return httpx2.Response(200, content=b"ok", request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    response = transport.handle_request(httpx2.Request("GET", "https://example.com/v1/models"))
    assert response.status_code == 200
    assert http.create_calls == 0
    assert calls["n"] == 2


def test_sync_hook_header_retry_still_402_falls_through() -> None:
    http = StubHttp(hook_headers={"Authorization": "Bearer x"})
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx2.Response(402, content=b"{}", request=request)
        assert request.headers["PAYMENT-SIGNATURE"] == "signed"
        return httpx2.Response(200, content=b"ok", request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    response = transport.handle_request(httpx2.Request("GET", "https://example.com/v1/models"))
    assert response.status_code == 200
    assert http.create_calls == 1
    assert calls["n"] == 3


def test_sync_streaming_200_body_not_consumed() -> None:
    http = StubHttp()

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=iter([b"chunk-a", b"chunk-b"]), request=request)

    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    response = transport.handle_request(httpx2.Request("GET", "https://example.com/v1/models"))
    assert response.status_code == 200
    assert response.read() == b"chunk-achunk-b"


def test_sync_close_closes_inner() -> None:
    inner = CloseTrackingTransport()
    transport = X402Httpx2SyncTransport(lambda: StubHttp(), inner=inner)
    transport.close()
    assert inner.closed is True


def test_sync_ensure_http_called_every_handle() -> None:
    counts = {"n": 0}

    def ensure() -> StubHttp:
        counts["n"] += 1
        return StubHttp()

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"ok", request=request)

    transport = X402Httpx2SyncTransport(ensure, inner=httpx2.MockTransport(handler))
    transport.handle_request(httpx2.Request("GET", "https://example.com/a"))
    transport.handle_request(httpx2.Request("GET", "https://example.com/b"))
    assert counts["n"] == 2


def test_sync_request_url_fallback() -> None:
    http = StubHttp(hook_headers={"Authorization": "Bearer x"})

    def handler(request: httpx2.Request) -> httpx2.Response:
        if not getattr(handler, "first", False):
            handler.first = True  # type: ignore[attr-defined]
            return httpx2.Response(402, content=b"{}")
        return httpx2.Response(200, content=b"ok")

    handler.first = False  # type: ignore[attr-defined]
    transport = X402Httpx2SyncTransport(lambda: http, inner=httpx2.MockTransport(handler))
    transport.handle_request(httpx2.Request("GET", "https://example.com/v1/models"))
    assert http.urls == ["https://example.com/v1/models"]


async def test_async_402_then_200() -> None:
    http = AsyncStubHttp()
    calls = {"n": 0}

    async def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx2.Response(402, content=b"{}", request=request)
        return httpx2.Response(200, content=b"ok", request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    response = await transport.handle_async_request(
        httpx2.Request("GET", "https://example.com/v1/models")
    )
    assert response.status_code == 200
    assert http.create_calls == 1


async def test_async_replays_streaming_body() -> None:
    http = AsyncStubHttp()
    bodies: list[bytes] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(await request.aread())
        if len(bodies) == 1:
            return httpx2.Response(402, content=b"{}", request=request)
        return httpx2.Response(200, content=b"ok", request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    async def stream() -> Any:
        yield b'{"prompt":'
        yield b'"hi"}'

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    response = await transport.handle_async_request(
        httpx2.Request("POST", "https://example.com/v1/chat", content=stream())
    )
    assert response.status_code == 200
    assert bodies == [b'{"prompt":"hi"}', b'{"prompt":"hi"}']


async def test_async_fail_closed() -> None:
    http = AsyncStubHttp(fail=True)

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(402, content=b"{}", request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    with pytest.raises(PaymentError, match="Failed to handle payment"):
        await transport.handle_async_request(httpx2.Request("GET", "https://example.com/x"))


async def test_async_no_retry_loop_on_recovery_key() -> None:
    http = AsyncStubHttp()
    calls = {"n": 0}

    async def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(402, content=b"{}", request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    request = httpx2.Request(
        "GET",
        "https://example.com/x",
        extensions={RECOVERY_KEY: True},
    )
    response = await transport.handle_async_request(request)
    assert response.status_code == 402
    assert calls["n"] == 1
    assert http.create_calls == 0


async def test_async_recovery() -> None:
    http = AsyncStubHttp(recovered=True)

    async def handler(request: httpx2.Request) -> httpx2.Response:
        if RECOVERY_KEY in request.extensions:
            return httpx2.Response(200, content=b"recovered", request=request)
        if RETRY_KEY in request.extensions:
            return httpx2.Response(200, content=b"paid", request=request)
        return httpx2.Response(402, content=b"{}", request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    response = await transport.handle_async_request(httpx2.Request("GET", "https://example.com/x"))
    assert await response.aread() == b"recovered"
    assert http.create_calls == 2


async def test_async_hook_skips_signing() -> None:
    http = AsyncStubHttp(hook_headers={"Authorization": "Bearer x"})
    calls = {"n": 0}

    async def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx2.Response(402, content=b"{}", request=request)
        return httpx2.Response(200, content=b"ok", request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    response = await transport.handle_async_request(httpx2.Request("GET", "https://example.com/x"))
    assert response.status_code == 200
    assert http.create_calls == 0


async def test_async_hook_still_402_falls_through() -> None:
    http = AsyncStubHttp(hook_headers={"Authorization": "Bearer x"})
    calls = {"n": 0}

    async def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx2.Response(402, content=b"{}", request=request)
        return httpx2.Response(200, content=b"ok", request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    response = await transport.handle_async_request(httpx2.Request("GET", "https://example.com/x"))
    assert response.status_code == 200
    assert http.create_calls == 1


async def test_async_streaming_200_not_consumed() -> None:
    http = AsyncStubHttp()

    async def handler(request: httpx2.Request) -> httpx2.Response:
        async def chunks() -> Any:
            yield b"a"
            yield b"b"

        return httpx2.Response(200, content=chunks(), request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    response = await transport.handle_async_request(httpx2.Request("GET", "https://example.com/x"))
    assert await response.aread() == b"ab"


async def test_async_aclose_closes_inner() -> None:
    inner = CloseTrackingAsyncTransport()

    async def ensure() -> AsyncStubHttp:
        return AsyncStubHttp()

    transport = X402Httpx2AsyncTransport(ensure, inner=inner)
    await transport.aclose()
    assert inner.closed is True


async def test_async_non_402_passthrough() -> None:
    http = AsyncStubHttp()

    async def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"ok", request=request)

    async def ensure() -> AsyncStubHttp:
        return http

    transport = X402Httpx2AsyncTransport(ensure, inner=RecordingAsyncTransport(handler))
    response = await transport.handle_async_request(httpx2.Request("GET", "https://example.com/x"))
    assert response.status_code == 200
    assert http.create_calls == 0
