"""Register SVM exact on ``solana:*``. Direct ``client.register``, no V1."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from x402 import x402Client, x402ClientSync

    from x402_openai._chains._types import SvmConfig


def register_svm(client: x402Client | x402ClientSync, config: SvmConfig) -> None:
    try:
        from x402.mechanisms.svm import KeypairSigner
        from x402.mechanisms.svm.exact import ExactSvmScheme
    except ImportError as e:
        raise ImportError(
            "SVM key provided but x402[svm] is not installed. pip install 'x402-openai[svm]'"
        ) from e

    signer = KeypairSigner.from_base58(config.private_key)
    client.register("solana:*", ExactSvmScheme(signer, rpc_url=config.rpc_url))
