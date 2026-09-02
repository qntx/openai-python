"""Normalize constructor chain fields and register official V2 schemes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qntx.openai._chains._evm import register_evm
from qntx.openai._chains._types import EvmConfig

if TYPE_CHECKING:
    from x402 import x402Client, x402ClientSync

    from qntx.openai._payments import PaymentSourceOptions


class ChainHandles:
    def dispose(self) -> None:
        # SVM/EVM RPC handles are owned upstream; they are not closed here.
        return None


def register_chains(
    client: x402Client | x402ClientSync,
    options: PaymentSourceOptions,
) -> ChainHandles:
    if options.evm is not None:
        register_evm(client, _normalize_evm(options.evm))
    return ChainHandles()


def _normalize_evm(evm: str | EvmConfig) -> EvmConfig:
    config = EvmConfig(private_key=evm) if isinstance(evm, str) else evm
    if not config.private_key:
        raise ValueError("'evm' private key must be a non-empty string.")
    return config
