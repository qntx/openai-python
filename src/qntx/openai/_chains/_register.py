"""Normalize constructor chain fields and register official V2 schemes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qntx.openai._chains._evm import register_evm
from qntx.openai._chains._svm import register_svm
from qntx.openai._chains._tvm import register_tvm
from qntx.openai._chains._types import EvmConfig, SvmConfig, TvmConfig

if TYPE_CHECKING:
    from x402 import x402Client, x402ClientSync

    from qntx.openai._chains._tvm import _TvmScheme
    from qntx.openai._payments import PaymentSourceOptions


class ChainHandles:
    def __init__(self, tvm_scheme: _TvmScheme | None = None) -> None:
        self._tvm_scheme = tvm_scheme

    def dispose(self) -> None:
        # EVM/SVM RPC handles have no close hook upstream.
        if self._tvm_scheme is not None:
            self._tvm_scheme.close()
            self._tvm_scheme = None


def register_chains(
    client: x402Client | x402ClientSync,
    options: PaymentSourceOptions,
) -> ChainHandles:
    tvm_scheme = None
    if options.evm is not None:
        register_evm(client, _normalize_evm(options.evm))
    if options.svm is not None:
        register_svm(client, _normalize_svm(options.svm))
    if options.tvm is not None:
        tvm_scheme = register_tvm(client, _normalize_tvm(options.tvm))
    return ChainHandles(tvm_scheme)


def _normalize_evm(evm: str | EvmConfig) -> EvmConfig:
    config = EvmConfig(private_key=evm) if isinstance(evm, str) else evm
    if not config.private_key:
        raise ValueError("'evm' private key must be a non-empty string.")
    return config


def _normalize_svm(svm: str | SvmConfig) -> SvmConfig:
    config = SvmConfig(private_key=svm) if isinstance(svm, str) else svm
    if not config.private_key:
        raise ValueError("'svm' private key must be a non-empty string.")
    return config


def _normalize_tvm(tvm: str | TvmConfig) -> TvmConfig:
    config = TvmConfig(private_key=tvm) if isinstance(tvm, str) else tvm
    if not config.private_key:
        raise ValueError("'tvm' private key must be a non-empty string.")
    return config
