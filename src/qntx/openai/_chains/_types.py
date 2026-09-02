"""Per-chain constructor config. Frozen dataclasses, no Pydantic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvmConfig:
    """EVM secp256k1 private key. ``rpc_url`` enables Permit2 gas sponsoring."""

    private_key: str
    rpc_url: str | None = None


@dataclass(frozen=True, slots=True)
class SvmConfig:
    """SVM base58 64-byte secret. ``rpc_url`` overrides the default Solana JSON-RPC."""

    private_key: str
    rpc_url: str | None = None
