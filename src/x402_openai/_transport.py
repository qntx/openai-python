"""httpx2 OpenAI integration: lazy x402 HTTP client, closed flag, 402 retry loop.

Retry loop is a port of official ``x402AsyncTransport.handle_async_request`` /
``_send_retry``. Do not import ``x402.http.clients.httpx`` (it imports httpx).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import httpx2

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from x402.http import x402HTTPClient, x402HTTPClientSync

logger = logging.getLogger("x402_openai")

RETRY_KEY = "_x402_is_retry"
RECOVERY_KEY = "_x402_is_recovery"


class PaymentError(Exception):
    """Base class for payment-related errors."""


def _retry_request(
    request: httpx2.Request,
    extra_headers: dict[str, str],
    *,
    payment_retry: bool = False,
    recovery_retry: bool = False,
) -> httpx2.Request:
    new_headers = dict(request.headers)
    new_headers.update(extra_headers)
    new_headers["Access-Control-Expose-Headers"] = "PAYMENT-RESPONSE,X-PAYMENT-RESPONSE"
    new_extensions = dict(request.extensions)
    if payment_retry:
        new_extensions[RETRY_KEY] = True
    if recovery_retry:
        new_extensions[RECOVERY_KEY] = True
    return httpx2.Request(
        method=request.method,
        url=request.url,
        headers=new_headers,
        content=request.content,
        extensions=new_extensions,
    )


def _request_url(response: httpx2.Response, request: httpx2.Request) -> str:
    try:
        request_url = str(response.url)
    except RuntimeError:
        request_url = ""
    return request_url or str(request.url)


def _parse_402_body(response: httpx2.Response) -> Any:
    try:
        return response.json()
    except json.JSONDecodeError:
        return None


class X402Httpx2SyncTransport(httpx2.BaseTransport):
    """Sync httpx2 transport: 402 → sign via x402HTTPClientSync → retry. Fail closed."""

    RETRY_KEY = RETRY_KEY
    RECOVERY_KEY = RECOVERY_KEY

    def __init__(
        self,
        ensure_http: Callable[[], x402HTTPClientSync],
        *,
        inner: httpx2.BaseTransport,
    ) -> None:
        self._ensure_http = ensure_http
        self._inner = inner

    def _send_retry(
        self,
        request: httpx2.Request,
        extra_headers: dict[str, str],
        *,
        payment_retry: bool = False,
        recovery_retry: bool = False,
    ) -> httpx2.Response:
        retry_request = _retry_request(
            request,
            extra_headers,
            payment_retry=payment_retry,
            recovery_retry=recovery_retry,
        )
        return self._inner.handle_request(retry_request)

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        http = self._ensure_http()
        # Buffer streaming bodies before the first send so retries preserve them.
        request.read()

        logger.debug("%s %s", request.method, request.url)
        response = self._inner.handle_request(request)

        if response.status_code != 402:
            return response

        if request.extensions.get(RETRY_KEY) or request.extensions.get(RECOVERY_KEY):
            return response

        logger.debug("received 402")
        try:
            response.read()
            get_header = response.headers.get
            body = _parse_402_body(response)
            payment_required = http.get_payment_required_response(get_header, body)
            request_url = _request_url(response, request)
            hook_headers = http.handle_payment_required(payment_required, request_url)
            if hook_headers:
                hook_response = self._send_retry(request, hook_headers)
                if hook_response.status_code != 402:
                    return hook_response

            payload = http.create_payment_payload(payment_required)
            headers = http.encode_payment_signature_header(payload)
            paid = self._send_retry(request, headers, payment_retry=True)
            process_result = http.process_payment_result(
                payload, paid.headers.get, paid.status_code
            )
            if process_result.recovered:
                fresh_payload = http.create_payment_payload(payment_required)
                fresh_headers = http.encode_payment_signature_header(fresh_payload)
                recovery_response = self._send_retry(request, fresh_headers, recovery_retry=True)
                http.process_payment_result(
                    fresh_payload,
                    recovery_response.headers.get,
                    recovery_response.status_code,
                )
                return recovery_response
            return paid
        except PaymentError:
            raise
        except Exception as e:
            raise PaymentError(f"Failed to handle payment: {e}") from e

    def close(self) -> None:
        self._inner.close()


class X402Httpx2AsyncTransport(httpx2.AsyncBaseTransport):
    """Async httpx2 transport: 402 → sign via x402HTTPClient → retry. Fail closed."""

    RETRY_KEY = RETRY_KEY
    RECOVERY_KEY = RECOVERY_KEY

    def __init__(
        self,
        ensure_http: Callable[[], Awaitable[x402HTTPClient]],
        *,
        inner: httpx2.AsyncBaseTransport,
    ) -> None:
        self._ensure_http = ensure_http
        self._inner = inner

    async def _send_retry(
        self,
        request: httpx2.Request,
        extra_headers: dict[str, str],
        *,
        payment_retry: bool = False,
        recovery_retry: bool = False,
    ) -> httpx2.Response:
        retry_request = _retry_request(
            request,
            extra_headers,
            payment_retry=payment_retry,
            recovery_retry=recovery_retry,
        )
        return await self._inner.handle_async_request(retry_request)

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        http = await self._ensure_http()
        # Buffer streaming bodies before the first send so retries preserve them.
        await request.aread()

        logger.debug("%s %s", request.method, request.url)
        response = await self._inner.handle_async_request(request)

        if response.status_code != 402:
            return response

        if request.extensions.get(RETRY_KEY) or request.extensions.get(RECOVERY_KEY):
            return response

        logger.debug("received 402")
        try:
            await response.aread()
            get_header = response.headers.get
            body = _parse_402_body(response)
            payment_required = http.get_payment_required_response(get_header, body)
            request_url = _request_url(response, request)
            hook_headers = await http.handle_payment_required(payment_required, request_url)
            if hook_headers:
                hook_response = await self._send_retry(request, hook_headers)
                if hook_response.status_code != 402:
                    return hook_response

            payload = await http.create_payment_payload(payment_required)
            headers = http.encode_payment_signature_header(payload)
            paid = await self._send_retry(request, headers, payment_retry=True)
            process_result = await http.process_payment_result(
                payload, paid.headers.get, paid.status_code
            )
            if process_result.recovered:
                fresh_payload = await http.create_payment_payload(payment_required)
                fresh_headers = http.encode_payment_signature_header(fresh_payload)
                recovery_response = await self._send_retry(
                    request, fresh_headers, recovery_retry=True
                )
                await http.process_payment_result(
                    fresh_payload,
                    recovery_response.headers.get,
                    recovery_response.status_code,
                )
                return recovery_response
            return paid
        except PaymentError:
            raise
        except Exception as e:
            raise PaymentError(f"Failed to handle payment: {e}") from e

    async def aclose(self) -> None:
        await self._inner.aclose()
