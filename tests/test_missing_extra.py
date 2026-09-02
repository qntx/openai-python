from __future__ import annotations

import sys

import pytest

from qntx.openai._chains._types import EvmConfig, SvmConfig


def test_missing_evm_extra_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name == "eth_account" or name.startswith("eth_account."):
            monkeypatch.setitem(sys.modules, name, None)
        if name == "x402.mechanisms.evm" or name.startswith("x402.mechanisms.evm."):
            monkeypatch.setitem(sys.modules, name, None)

    from qntx.openai._chains._evm import register_evm

    class _Client:
        def register(self, network: str, scheme: object) -> None:
            return None

    with pytest.raises(ImportError, match=r"qntx-openai\[evm\]"):
        register_evm(_Client(), EvmConfig(private_key="0x1"))  # type: ignore[arg-type]


def test_missing_svm_extra_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name == "solders" or name.startswith("solders."):
            monkeypatch.setitem(sys.modules, name, None)
        if name == "solana" or name.startswith("solana."):
            monkeypatch.setitem(sys.modules, name, None)
        if name == "x402.mechanisms.svm" or name.startswith("x402.mechanisms.svm."):
            monkeypatch.setitem(sys.modules, name, None)

    from qntx.openai._chains._svm import register_svm

    class _Client:
        def register(self, network: str, scheme: object) -> None:
            return None

    with pytest.raises(ImportError, match=r"qntx-openai\[svm\]"):
        register_svm(_Client(), SvmConfig(private_key="base58"))  # type: ignore[arg-type]
