"""Drop-in OpenAI clients with transparent x402 payment."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, Self

import httpx2
import openai
from httpx2._utils import get_environment_proxies
from openai import DefaultAsyncHttpx2Client, DefaultHttpx2Client

from x402_openai._payments import (
    BuiltClient,
    PaymentSourceOptions,
    assert_payment_options,
    build_x402_client,
)
from x402_openai._transport import X402Httpx2AsyncTransport, X402Httpx2SyncTransport

if TYPE_CHECKING:
    from x402 import SpendControls, x402Client, x402ClientSync

    from x402_openai._chains._types import EvmConfig, SvmConfig, TvmConfig

DEFAULT_BASE_URL = "https://llm.qntx.org/v1"
_REMOVED = ("wallet", "wallets", "mnemonic", "max_amount", "http_client")
_NOT_YET: dict[str, str] = {}
_HTTP_CLIENT_REMOVED = (
    "'http_client' was removed. Pass per-chain private keys (evm=) and spend_controls=."
)

Policy = Callable[[int, list[Any]], list[Any]]
Selector = Callable[[int, list[Any]], Any]


def _inner_kwargs(proxy: str | None = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"limits": openai.DEFAULT_CONNECTION_LIMITS}
    if proxy is not None:
        kwargs["proxy"] = proxy
    return kwargs


def _env_proxy_mounts(ensure_http: Callable[..., Any], *, async_inner: bool) -> dict[str, Any]:
    mounts: dict[str, Any] = {}
    for key, url in get_environment_proxies().items():
        if url is None:
            mounts[key] = None
            continue
        inner_kw = _inner_kwargs(url)
        if async_inner:
            mounts[key] = X402Httpx2AsyncTransport(
                ensure_http, inner=httpx2.AsyncHTTPTransport(**inner_kw)
            )
        else:
            mounts[key] = X402Httpx2SyncTransport(
                ensure_http, inner=httpx2.HTTPTransport(**inner_kw)
            )
    return mounts


class _SyncLifecycle:
    def __init__(self, options: PaymentSourceOptions) -> None:
        self._options = options
        self._closed = False
        self._built: BuiltClient | None = None
        self.http_client = DefaultHttpx2Client(
            transport=X402Httpx2SyncTransport(
                self._ensure_http,
                inner=httpx2.HTTPTransport(**_inner_kwargs()),
            ),
            mounts=_env_proxy_mounts(self._ensure_http, async_inner=False),
            timeout=openai.DEFAULT_TIMEOUT,
        )

    def _ensure_http(self) -> Any:
        if self._closed:
            raise RuntimeError("X402OpenAI is closed")
        if self._built is None:
            self._built = build_x402_client(self._options, sync=True)
        if self._closed:
            self._built.dispose()
            self._built = None
            raise RuntimeError("X402OpenAI is closed")
        return self._built.http

    def close(self) -> None:
        self._closed = True
        if self._built is not None:
            self._built.dispose()
            self._built = None


class _AsyncLifecycle:
    def __init__(self, options: PaymentSourceOptions) -> None:
        self._options = options
        self._closed = False
        self._built: BuiltClient | None = None
        self._lock = asyncio.Lock()
        self.http_client = DefaultAsyncHttpx2Client(
            transport=X402Httpx2AsyncTransport(
                self._ensure_http,
                inner=httpx2.AsyncHTTPTransport(**_inner_kwargs()),
            ),
            mounts=_env_proxy_mounts(self._ensure_http, async_inner=True),
            timeout=openai.DEFAULT_TIMEOUT,
        )

    async def _ensure_http(self) -> Any:
        if self._closed:
            raise RuntimeError("X402OpenAI is closed")
        if self._built is not None:
            return self._built.http
        async with self._lock:
            if self._closed:
                raise RuntimeError("X402OpenAI is closed")
            if self._built is None:
                self._built = build_x402_client(self._options, sync=False)
            if self._closed:
                self._built.dispose()
                self._built = None
                raise RuntimeError("X402OpenAI is closed")
            return self._built.http

    def close(self) -> None:
        self._closed = True
        if self._built is not None:
            self._built.dispose()
            self._built = None

    async def aclose(self) -> None:
        self._closed = True
        async with self._lock:
            if self._built is not None:
                self._built.dispose()
                self._built = None


def _reject_removed_and_not_yet(kwargs: dict[str, Any]) -> None:
    for name in _REMOVED:
        if name in kwargs:
            raise TypeError(
                f"{name!r} was removed. Pass per-chain private keys (evm=) and spend_controls=."
            )
    for name, msg in _NOT_YET.items():
        if name in kwargs:
            raise TypeError(msg)


def _copy_with_lifecycle(self: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    if kwargs.get("http_client") is not None:
        raise TypeError(_HTTP_CLIENT_REMOVED)
    extra = dict(kwargs.get("_extra_kwargs") or {})
    extra["_lifecycle"] = self._lifecycle
    kwargs["_extra_kwargs"] = extra
    return kwargs


class X402OpenAI(openai.OpenAI):
    """Synchronous OpenAI client with transparent x402 payment.

    Provide at least one of ``evm``, ``svm``, ``tvm``, or ``x402_client``. Default
    ``base_url`` is ``https://llm.qntx.org/v1``.
    """

    def __init__(
        self,
        *,
        evm: str | EvmConfig | None = None,
        svm: str | SvmConfig | None = None,
        tvm: str | TvmConfig | None = None,
        spend_controls: SpendControls | Literal[False] | None = None,
        policies: list[Policy] | None = None,
        payment_requirements_selector: Selector | None = None,
        x402_client: x402ClientSync | None = None,
        base_url: str | httpx2.URL | None = None,
        api_key: str | None = "x402",
        **kwargs: Any,
    ) -> None:
        lifecycle = kwargs.pop("_lifecycle", None)
        if lifecycle is not None:
            kwargs.pop("http_client", None)
            _reject_removed_and_not_yet(kwargs)
            super().__init__(
                api_key=api_key,
                base_url=base_url or DEFAULT_BASE_URL,
                http_client=lifecycle.http_client,
                **kwargs,
            )
            self._lifecycle = lifecycle
            return
        _reject_removed_and_not_yet(kwargs)
        payment = PaymentSourceOptions(
            evm=evm,
            svm=svm,
            tvm=tvm,
            spend_controls=spend_controls,
            policies=policies,
            payment_requirements_selector=payment_requirements_selector,
            x402_client=x402_client,
        )
        assert_payment_options(payment)
        lifecycle = _SyncLifecycle(payment)
        super().__init__(
            api_key=api_key,
            base_url=base_url or DEFAULT_BASE_URL,
            http_client=lifecycle.http_client,
            **kwargs,
        )
        self._lifecycle = lifecycle

    def copy(self, **kwargs: Any) -> Self:
        return super().copy(**_copy_with_lifecycle(self, kwargs))

    with_options = copy

    def close(self) -> None:
        self._lifecycle.close()
        super().close()


class AsyncX402OpenAI(openai.AsyncOpenAI):
    """Asynchronous OpenAI client with transparent x402 payment.

    Same payment parameters as :class:`X402OpenAI`.
    """

    def __init__(
        self,
        *,
        evm: str | EvmConfig | None = None,
        svm: str | SvmConfig | None = None,
        tvm: str | TvmConfig | None = None,
        spend_controls: SpendControls | Literal[False] | None = None,
        policies: list[Policy] | None = None,
        payment_requirements_selector: Selector | None = None,
        x402_client: x402Client | None = None,
        base_url: str | httpx2.URL | None = None,
        api_key: str | None = "x402",
        **kwargs: Any,
    ) -> None:
        lifecycle = kwargs.pop("_lifecycle", None)
        if lifecycle is not None:
            kwargs.pop("http_client", None)
            _reject_removed_and_not_yet(kwargs)
            super().__init__(
                api_key=api_key,
                base_url=base_url or DEFAULT_BASE_URL,
                http_client=lifecycle.http_client,
                **kwargs,
            )
            self._lifecycle = lifecycle
            return
        _reject_removed_and_not_yet(kwargs)
        payment = PaymentSourceOptions(
            evm=evm,
            svm=svm,
            tvm=tvm,
            spend_controls=spend_controls,
            policies=policies,
            payment_requirements_selector=payment_requirements_selector,
            x402_client=x402_client,
        )
        assert_payment_options(payment)
        lifecycle = _AsyncLifecycle(payment)
        super().__init__(
            api_key=api_key,
            base_url=base_url or DEFAULT_BASE_URL,
            http_client=lifecycle.http_client,
            **kwargs,
        )
        self._lifecycle = lifecycle

    def copy(self, **kwargs: Any) -> Self:
        return super().copy(**_copy_with_lifecycle(self, kwargs))

    with_options = copy

    async def close(self) -> None:
        await self._lifecycle.aclose()
        await super().close()

    async def aclose(self) -> None:
        await self.close()
