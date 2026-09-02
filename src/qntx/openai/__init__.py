"""qntx-openai — Drop-in OpenAI client with transparent x402 payment.

Quick start::

    from qntx.openai import prefer_scheme, X402OpenAI

    client = X402OpenAI(evm="0x…")

    multi = X402OpenAI(
        evm="0x…",
        svm="base58…",
        spend_controls={"max_amount_per_payment": "$0.50"},
        policies=[prefer_scheme("upto")],
    )

Public API:

- :class:`X402OpenAI` / :class:`AsyncX402OpenAI` — recommended client classes.
- :func:`prefer_network` / :func:`prefer_scheme` — payment preference policies.
- :class:`EvmConfig` / :class:`SvmConfig` / :data:`SpendControls` — constructor config types.
"""

from __future__ import annotations

from x402 import SpendControls, x402Client, x402ClientSync

from qntx.openai._chains._types import EvmConfig, SvmConfig
from qntx.openai._client import AsyncX402OpenAI, X402OpenAI
from qntx.openai._policies import prefer_network, prefer_scheme

__all__ = [
    "AsyncX402OpenAI",
    "EvmConfig",
    "SpendControls",
    "SvmConfig",
    "X402OpenAI",
    "prefer_network",
    "prefer_scheme",
    "x402Client",
    "x402ClientSync",
]
