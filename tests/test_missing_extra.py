from __future__ import annotations

import sys

import pytest

from x402_openai._chains._types import EvmConfig, SvmConfig, TvmConfig


def test_missing_evm_extra_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "eth_account", None)
    monkeypatch.setitem(sys.modules, "x402.mechanisms.evm", None)
    for name in list(sys.modules):
        if name.startswith("eth_account.") or name.startswith("x402.mechanisms.evm."):
            monkeypatch.setitem(sys.modules, name, None)

    from x402_openai._chains._evm import register_evm

    class _Client:
        def register(self, network: str, scheme: object) -> None:
            return None

    with pytest.raises(ImportError, match=r"x402-openai\[evm\]"):
        register_evm(_Client(), EvmConfig(private_key="0x1"))  # type: ignore[arg-type]


def test_missing_svm_extra_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name == "solders" or name.startswith("solders."):
            monkeypatch.setitem(sys.modules, name, None)
        if name == "solana" or name.startswith("solana."):
            monkeypatch.setitem(sys.modules, name, None)
        if name == "x402.mechanisms.svm" or name.startswith("x402.mechanisms.svm."):
            monkeypatch.setitem(sys.modules, name, None)

    from x402_openai._chains._svm import register_svm

    class _Client:
        def register(self, network: str, scheme: object) -> None:
            return None

    with pytest.raises(ImportError, match=r"x402-openai\[svm\]"):
        register_svm(_Client(), SvmConfig(private_key="base58"))  # type: ignore[arg-type]


def test_missing_tvm_extra_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pytoniq", None)
    monkeypatch.setitem(sys.modules, "pytoniq_core", None)
    monkeypatch.setitem(sys.modules, "x402.mechanisms.tvm", None)
    for name in list(sys.modules):
        if (
            name.startswith("pytoniq.")
            or name.startswith("pytoniq_core.")
            or name.startswith("x402.mechanisms.tvm.")
        ):
            monkeypatch.setitem(sys.modules, name, None)

    from x402_openai._chains._tvm import register_tvm

    class _Client:
        def register(self, network: str, scheme: object) -> None:
            return None

    with pytest.raises(ImportError, match=r"x402-openai\[tvm\]"):
        register_tvm(_Client(), TvmConfig(private_key="11" * 32))  # type: ignore[arg-type]
