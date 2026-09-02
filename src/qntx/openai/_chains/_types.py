"""Per-chain constructor config. Frozen dataclasses, no Pydantic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvmConfig:
    """EVM secp256k1 private key. ``rpc_url`` enables Permit2 gas sponsoring."""

    private_key: str
    rpc_url: str | None = None
