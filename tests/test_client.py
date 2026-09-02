from __future__ import annotations

import asyncio
import threading
from typing import Any
from unittest.mock import patch

import httpx2
import openai
import pytest
from x402 import x402Client, x402ClientSync

import qntx.openai as api
from qntx.openai import AsyncX402OpenAI, X402OpenAI
from qntx.openai._payments import BuiltClient

EVM_KEY = "0xac0974dac38f24671676c33098b7abf185c4d7b8d04844c06a56a24126c6dcbd"


def test_defaults_base_url() -> None:
    client = X402OpenAI(evm="0x1")
    assert str(client.base_url).rstrip("/") == "https://llm.qntx.org/v1"


def test_async_defaults_base_url() -> None:
    client = AsyncX402OpenAI(evm="0x1")
    assert str(client.base_url).rstrip("/") == "https://llm.qntx.org/v1"


def test_is_openai_subclass() -> None:
    client = X402OpenAI(evm="0x1")
    assert isinstance(client, openai.OpenAI)


def test_throws_when_no_credentials() -> None:
    with pytest.raises(ValueError, match="at least one"):
        X402OpenAI()


def test_throws_on_empty_evm_string() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        X402OpenAI(evm="")


def test_throws_on_empty_evm_config() -> None:
    from qntx.openai import EvmConfig

    with pytest.raises(ValueError, match="non-empty"):
        X402OpenAI(evm=EvmConfig(private_key=""))


def test_throws_on_removed_names() -> None:
    for name in ("wallet", "wallets", "mnemonic", "max_amount", "http_client"):
        with pytest.raises(TypeError, match="was removed"):
            X402OpenAI(evm="0x1", **{name: object()})


def test_http_client_typeerror() -> None:
    with pytest.raises(TypeError, match="http_client"):
        X402OpenAI(evm="0x1", http_client=object())


def test_svm_not_yet() -> None:
    with pytest.raises(TypeError, match="svm="):
        X402OpenAI(evm="0x1", svm="base58")


def test_tvm_not_yet() -> None:
    with pytest.raises(TypeError, match="tvm="):
        X402OpenAI(evm="0x1", tvm="00")


def test_prebuilt_exclusive_with_evm() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        X402OpenAI(x402_client=x402ClientSync(), evm="0x1")


def test_prebuilt_exclusive_with_policies() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        X402OpenAI(x402_client=x402ClientSync(), policies=[lambda _v, reqs: reqs])


def test_prebuilt_exclusive_with_spend_controls() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        X402OpenAI(
            x402_client=x402ClientSync(),
            spend_controls={"max_amount_per_payment": "$5"},
        )


def test_prebuilt_exclusive_with_selector() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        X402OpenAI(
            x402_client=x402ClientSync(),
            payment_requirements_selector=lambda _v, reqs: reqs[0],
        )


def test_accepts_prebuilt_alone() -> None:
    client = X402OpenAI(x402_client=x402ClientSync())
    assert isinstance(client, X402OpenAI)


def test_accepts_spend_controls_with_keys() -> None:
    client = X402OpenAI(
        evm="0x1",
        spend_controls={"max_amount_per_payment": "$5"},
        payment_requirements_selector=lambda _v, reqs: reqs[0],
    )
    assert isinstance(client, X402OpenAI)


def test_close_before_build_is_noop() -> None:
    client = X402OpenAI(evm=EVM_KEY)
    client.close()
    assert client._lifecycle._built is None


def test_request_after_close_raises_and_does_not_rebuild() -> None:
    client = X402OpenAI(evm=EVM_KEY)
    client.close()
    with pytest.raises(RuntimeError, match="X402OpenAI is closed"):
        client._lifecycle._ensure_http()
    assert client._lifecycle._built is None
    with pytest.raises(RuntimeError, match="X402OpenAI is closed"):
        client._lifecycle._ensure_http()
    assert client._lifecycle._built is None


def test_close_concurrent_with_first_request_disposes_and_raises() -> None:
    dispose_calls = 0

    def dispose() -> None:
        nonlocal dispose_calls
        dispose_calls += 1

    built_started = threading.Event()
    continue_build = threading.Event()

    def fake_build(options: object, *, sync: bool) -> BuiltClient:
        built_started.set()
        assert continue_build.wait(timeout=2)
        return BuiltClient(http=object(), dispose=dispose)

    client = X402OpenAI(evm=EVM_KEY)
    errors: list[BaseException] = []

    def run_ensure() -> None:
        try:
            client._lifecycle._ensure_http()
        except BaseException as e:
            errors.append(e)

    with patch("qntx.openai._client.build_x402_client", fake_build):
        thread = threading.Thread(target=run_ensure)
        thread.start()
        assert built_started.wait(timeout=2)
        client.close()
        continue_build.set()
        thread.join(timeout=2)

    assert any(isinstance(e, RuntimeError) and "X402OpenAI is closed" in str(e) for e in errors)
    assert dispose_calls == 1
    assert client._lifecycle._built is None


async def test_async_two_concurrent_first_requests_build_once() -> None:
    builds = 0

    def fake_build(options: object, *, sync: bool) -> BuiltClient:
        nonlocal builds
        builds += 1
        return BuiltClient(http=object(), dispose=lambda: None)

    client = AsyncX402OpenAI(evm=EVM_KEY)
    with patch("qntx.openai._client.build_x402_client", fake_build):
        h1, h2 = await asyncio.gather(
            client._lifecycle._ensure_http(),
            client._lifecycle._ensure_http(),
        )
    assert builds == 1
    assert h1 is h2


async def test_async_close_before_build_is_noop() -> None:
    client = AsyncX402OpenAI(evm=EVM_KEY)
    await client.aclose()
    assert client._lifecycle._built is None


async def test_async_request_after_close_raises() -> None:
    client = AsyncX402OpenAI(evm=EVM_KEY)
    await client.aclose()
    with pytest.raises(RuntimeError, match="X402OpenAI is closed"):
        await client._lifecycle._ensure_http()


def test_public_api_does_not_export_removed_names() -> None:
    assert not hasattr(api, "EvmWallet")
    assert not hasattr(api, "SvmWallet")
    assert not hasattr(api, "Wallet")
    assert not hasattr(api, "max_amount")
    assert not hasattr(api, "PaymentError")
    assert not hasattr(api, "X402Transport")


def test_async_prebuilt_uses_async_client() -> None:
    client = AsyncX402OpenAI(x402_client=x402Client())
    assert isinstance(client, AsyncX402OpenAI)


def test_removed_names_never_reach_openai() -> None:
    """svm/tvm must TypeError before OpenAI sees them as kwargs."""
    with pytest.raises(TypeError, match="svm="):
        X402OpenAI(svm="x")
    with pytest.raises(TypeError, match="tvm="):
        X402OpenAI(tvm="x")


def test_copy_reuses_lifecycle_and_http_client() -> None:
    client = X402OpenAI(evm="0x1")
    copied = client.copy()
    assert copied is not client
    assert copied._lifecycle is client._lifecycle
    assert copied._client is client._client


def test_with_options_timeout_reuses_lifecycle() -> None:
    client = X402OpenAI(evm="0x1")
    copied = client.with_options(timeout=10)
    assert copied.timeout == 10
    assert copied._lifecycle is client._lifecycle


def test_copy_rejects_caller_http_client() -> None:
    client = X402OpenAI(evm="0x1")
    with pytest.raises(TypeError, match="http_client"):
        client.copy(http_client=httpx2.Client())


def test_constructor_still_rejects_http_client() -> None:
    with pytest.raises(TypeError, match="http_client"):
        X402OpenAI(evm="0x1", http_client=httpx2.Client())


def test_async_copy_reuses_lifecycle() -> None:
    client = AsyncX402OpenAI(evm="0x1")
    copied = client.copy()
    assert copied._lifecycle is client._lifecycle
    assert copied.with_options(timeout=5)._lifecycle is client._lifecycle


async def test_async_close_during_first_request_observes_closed() -> None:
    dispose_calls = 0

    def dispose() -> None:
        nonlocal dispose_calls
        dispose_calls += 1

    client = AsyncX402OpenAI(evm=EVM_KEY)
    lifecycle = client._lifecycle

    def fake_build(options: object, *, sync: bool) -> BuiltClient:
        return BuiltClient(http=object(), dispose=dispose)

    await lifecycle._lock.acquire()
    try:
        with patch("qntx.openai._client.build_x402_client", fake_build):
            ensure_task = asyncio.create_task(lifecycle._ensure_http())
            await asyncio.sleep(0)
            close_task = asyncio.create_task(client.close())
            await asyncio.sleep(0)
            assert lifecycle._closed is True
            lifecycle._lock.release()
            results = await asyncio.gather(ensure_task, close_task, return_exceptions=True)
    except BaseException:
        if lifecycle._lock.locked():
            lifecycle._lock.release()
        raise

    assert any(isinstance(r, RuntimeError) and "X402OpenAI is closed" in str(r) for r in results)


async def test_async_close_during_build_disposes_just_built_client() -> None:
    dispose_calls = 0

    def dispose() -> None:
        nonlocal dispose_calls
        dispose_calls += 1

    client = AsyncX402OpenAI(evm=EVM_KEY)
    lifecycle = client._lifecycle

    def fake_build(options: object, *, sync: bool) -> BuiltClient:
        lifecycle._closed = True
        return BuiltClient(http=object(), dispose=dispose)

    with (
        patch("qntx.openai._client.build_x402_client", fake_build),
        pytest.raises(RuntimeError, match="X402OpenAI is closed"),
    ):
        await lifecycle._ensure_http()
    assert dispose_calls == 1
    assert lifecycle._built is None


def test_inner_transport_uses_openai_limits_and_env_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    real = httpx2.HTTPTransport

    def capturing_transport(*args: Any, **kwargs: Any) -> httpx2.HTTPTransport:
        captured.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr("qntx.openai._client.httpx2.HTTPTransport", capturing_transport)
    monkeypatch.setattr(
        "qntx.openai._client.get_environment_proxies",
        lambda: {"https://": "http://proxy.example:8080"},
    )
    X402OpenAI(evm="0x1")
    assert captured
    assert all(k.get("limits") == openai.DEFAULT_CONNECTION_LIMITS for k in captured)
    assert any(k.get("proxy") == "http://proxy.example:8080" for k in captured)
