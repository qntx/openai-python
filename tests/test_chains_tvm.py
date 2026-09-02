from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from qntx.openai._chains._register import register_chains
from qntx.openai._chains._tvm import register_tvm
from qntx.openai._chains._types import TvmConfig
from qntx.openai._payments import PaymentSourceOptions, build_x402_client

TVM_KEY = "11" * 32


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def register(self, network: str, scheme: object) -> None:
        self.calls.append((network, scheme))


class _StubWalletConfig:
    from_mnemonic_calls = 0

    def __init__(self) -> None:
        self.network: str | None = None
        self.secret_key: object = None
        self.provider = "toncenter"
        self.api_key: str | None = None
        self.provider_base_url: str | None = None

    @classmethod
    def from_private_key(
        cls, network: str, private_key: str, **kwargs: object
    ) -> _StubWalletConfig:
        cfg = cls()
        cfg.network = network
        cfg.secret_key = private_key
        return cfg

    @classmethod
    def from_mnemonic(cls, *args: object, **kwargs: object) -> _StubWalletConfig:
        cls.from_mnemonic_calls += 1
        raise AssertionError("from_mnemonic must not be called")


class _StubSigner:
    def __init__(self, config: _StubWalletConfig) -> None:
        self.config = config


class _StubExactTvmScheme:
    scheme = "exact"

    def __init__(self, signer: _StubSigner) -> None:
        self._signer = signer
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


@pytest.fixture
def tvm_stubs(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    _StubWalletConfig.from_mnemonic_calls = 0
    tvm_mod = types.ModuleType("x402.mechanisms.tvm")
    tvm_mod.__path__ = []  # type: ignore[attr-defined]
    tvm_mod.TVM_MAINNET = "tvm:-239"
    tvm_mod.TVM_TESTNET = "tvm:-3"
    tvm_mod.WalletV5R1Config = _StubWalletConfig
    tvm_mod.WalletV5R1MnemonicSigner = _StubSigner
    exact_mod = types.ModuleType("x402.mechanisms.tvm.exact")
    exact_mod.ExactTvmScheme = _StubExactTvmScheme
    tvm_mod.exact = exact_mod
    monkeypatch.setitem(sys.modules, "x402.mechanisms.tvm", tvm_mod)
    monkeypatch.setitem(sys.modules, "x402.mechanisms.tvm.exact", exact_mod)
    return tvm_mod


def test_register_tvm_default_network_not_wildcard(tvm_stubs: types.ModuleType) -> None:
    client = _RecordingClient()
    scheme = register_tvm(client, TvmConfig(private_key=TVM_KEY))  # type: ignore[arg-type]
    assert len(client.calls) == 1
    assert client.calls[0][0] == "tvm:-239"
    assert isinstance(client.calls[0][1], _StubExactTvmScheme)
    assert "tvm:*" not in [network for network, _ in client.calls]
    assert scheme is client.calls[0][1]
    assert _StubWalletConfig.from_mnemonic_calls == 0


def test_register_tvm_configured_caip2_not_wildcard(tvm_stubs: types.ModuleType) -> None:
    client = _RecordingClient()
    register_tvm(  # type: ignore[arg-type]
        client,  # type: ignore[arg-type]
        TvmConfig(private_key=TVM_KEY, network="tvm:-3", provider="toncenter"),
    )
    assert client.calls[0][0] == "tvm:-3"
    assert "tvm:*" not in [network for network, _ in client.calls]


def test_register_tvm_applies_provider_fields(tvm_stubs: types.ModuleType) -> None:
    client = _RecordingClient()
    scheme = register_tvm(  # type: ignore[arg-type]
        client,  # type: ignore[arg-type]
        TvmConfig(
            private_key=TVM_KEY,
            provider="tonapi",
            api_key="k",
            provider_base_url="https://tonapi.example",
        ),
    )
    cfg = scheme._signer.config  # type: ignore[attr-defined]
    assert cfg.provider == "tonapi"
    assert cfg.api_key == "k"
    assert cfg.provider_base_url == "https://tonapi.example"
    assert cfg.secret_key == TVM_KEY


def test_register_chains_string_tvm_not_wildcard(tvm_stubs: types.ModuleType) -> None:
    client = _RecordingClient()
    handles = register_chains(
        client,  # type: ignore[arg-type]
        PaymentSourceOptions(tvm=TVM_KEY),
    )
    assert len(client.calls) == 1
    assert client.calls[0][0] == "tvm:-239"
    assert "tvm:*" not in [network for network, _ in client.calls]
    handles.dispose()


def test_dispose_calls_scheme_close_once(tvm_stubs: types.ModuleType) -> None:
    client = _RecordingClient()
    handles = register_chains(
        client,  # type: ignore[arg-type]
        PaymentSourceOptions(tvm=TVM_KEY),
    )
    scheme = client.calls[0][1]
    assert isinstance(scheme, _StubExactTvmScheme)
    handles.dispose()
    handles.dispose()
    assert scheme.close_calls == 1


def test_build_registers_exact_on_tvm_mainnet_not_wildcard(
    tvm_stubs: types.ModuleType,
) -> None:
    built = build_x402_client(PaymentSourceOptions(tvm=TVM_KEY), sync=True)
    core = built.http._client
    schemes: dict[str, Any] = core._schemes["tvm:-239"]
    assert "tvm:*" not in core._schemes
    assert isinstance(schemes["exact"], _StubExactTvmScheme)
    built.dispose()


def test_build_dispose_calls_scheme_close(tvm_stubs: types.ModuleType) -> None:
    built = build_x402_client(PaymentSourceOptions(tvm=TVM_KEY), sync=True)
    scheme = built.http._client._schemes["tvm:-239"]["exact"]
    assert isinstance(scheme, _StubExactTvmScheme)
    built.dispose()
    built.dispose()
    assert scheme.close_calls == 1


def test_build_normalizes_tvm_config_object(tvm_stubs: types.ModuleType) -> None:
    built = build_x402_client(
        PaymentSourceOptions(tvm=TvmConfig(private_key=TVM_KEY, network="tvm:-3")),
        sync=True,
    )
    core = built.http._client
    assert "tvm:-3" in core._schemes
    assert "tvm:-239" not in core._schemes
    assert "tvm:*" not in core._schemes
    built.dispose()


def test_register_tvm_real_import_from_private_key() -> None:
    pytest.importorskip("pytoniq")
    from x402.mechanisms.tvm.exact import ExactTvmScheme

    client = _RecordingClient()
    scheme = register_tvm(client, TvmConfig(private_key=TVM_KEY))  # type: ignore[arg-type]
    assert client.calls[0][0] == "tvm:-239"
    assert isinstance(client.calls[0][1], ExactTvmScheme)
    assert "tvm:*" not in [network for network, _ in client.calls]
    scheme.close()


def test_invalid_key_is_not_missing_extra() -> None:
    pytest.importorskip("pytoniq")
    client = _RecordingClient()
    with pytest.raises(ValueError) as exc:
        register_tvm(client, TvmConfig(private_key="00"))  # type: ignore[arg-type]
    assert "not installed" not in str(exc.value)
    assert "qntx-openai[tvm]" not in str(exc.value)


def test_dispose_mocks_real_scheme_close(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("pytoniq")
    from x402.mechanisms.tvm.exact import ExactTvmScheme

    close_calls = 0
    original = ExactTvmScheme.close

    def wrapped(self: ExactTvmScheme) -> None:
        nonlocal close_calls
        close_calls += 1
        original(self)

    monkeypatch.setattr(ExactTvmScheme, "close", wrapped)
    built = build_x402_client(PaymentSourceOptions(tvm=TVM_KEY), sync=True)
    built.dispose()
    assert close_calls == 1
    built.dispose()
    assert close_calls == 1
