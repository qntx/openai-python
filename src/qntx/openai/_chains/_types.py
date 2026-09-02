"""Per-chain constructor config. Frozen dataclasses, no Pydantic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


@dataclass(frozen=True, slots=True)
class TvmConfig:
    """TVM hex/base64 seed or secret. Registers exact on ``tvm:-239`` by default.

    The 402 must set ``extra.areFeesSponsored`` to True.
    """

    private_key: str
    network: Literal["tvm:-239", "tvm:-3"] | None = None
    provider: str | None = None
    api_key: str | None = None
    provider_base_url: str | None = None
