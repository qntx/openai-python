"""Normalize constructor chain fields and register official V2 schemes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qntx.openai._chains._evm import register_evm
from qntx.openai._chains._svm import register_svm
from qntx.openai._chains._types import EvmConfig, SvmConfig

if TYPE_CHECKING:
    from x402 import x402Client, x402ClientSync

    from qntx.openai._payments import PaymentSourceOptions


class ChainHandles:
    def dispose(self) -> None:
        # EVM/SVM RPC handles have no close hook upstream.
        return None


def register_chains(
    client: x402Client | x402ClientSync,
    options: PaymentSourceOptions,
) -> ChainHandles:
    if options.evm is not None:
        register_evm(client, _normalize_evm(options.evm))
    if options.svm is not None:
        register_svm(client, _normalize_svm(options.svm))
    return ChainHandles()


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
