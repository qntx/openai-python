"""Register EVM exact + upto on ``eip155:*``. Direct ``client.register``, no V1."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from x402 import x402Client, x402ClientSync

    from x402_openai._chains._types import EvmConfig


def register_evm(client: x402Client | x402ClientSync, config: EvmConfig) -> None:
    try:
        from eth_account import Account
        from x402.mechanisms.evm.exact import ExactEvmScheme
        from x402.mechanisms.evm.upto import UptoEvmScheme
    except ImportError as e:
        raise ImportError(
            "EVM key provided but x402[evm] is not installed. pip install 'x402-openai[evm]'"
        ) from e

    account = Account.from_key(config.private_key)
    if config.rpc_url:
        from x402.mechanisms.evm.signers import EthAccountSignerWithRPC

        signer = EthAccountSignerWithRPC(account, config.rpc_url)
    else:
        signer = account  # ExactEvmScheme / UptoEvmScheme auto-wrap LocalAccount
    client.register("eip155:*", ExactEvmScheme(signer))
    client.register("eip155:*", UptoEvmScheme(signer))
