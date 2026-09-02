"""Register TVM exact on a concrete CAIP-2. Direct ``client.register``, no V1."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from x402 import x402Client, x402ClientSync

    from qntx.openai._chains._types import TvmConfig


class _TvmScheme(Protocol):
    def close(self) -> None: ...


def register_tvm(client: x402Client | x402ClientSync, config: TvmConfig) -> _TvmScheme:
    try:
        from x402.mechanisms.tvm import (
            TVM_MAINNET,
            WalletV5R1Config,
            WalletV5R1MnemonicSigner,  # official class; private-key path only
        )
        from x402.mechanisms.tvm.exact import ExactTvmScheme
    except ImportError as e:
        raise ImportError(
            "TVM key provided but x402[tvm] is not installed. pip install 'qntx-openai[tvm]'"
        ) from e

    network = config.network or TVM_MAINNET
    cfg = WalletV5R1Config.from_private_key(network, config.private_key)
    if config.provider is not None:
        cfg.provider = config.provider
    if config.api_key is not None:
        cfg.api_key = config.api_key
    if config.provider_base_url is not None:
        cfg.provider_base_url = config.provider_base_url
    signer = WalletV5R1MnemonicSigner(cfg)
    scheme = ExactTvmScheme(signer)
    client.register(network, scheme)
    return scheme
