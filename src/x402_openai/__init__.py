"""x402-openai — Drop-in OpenAI client with transparent x402 payment.

Quick start::

    from x402_openai import prefer_scheme, X402OpenAI

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
- :class:`EvmConfig` / :class:`SvmConfig` / :class:`TvmConfig` / :data:`SpendControls`.
"""

from __future__ import annotations

from x402 import SpendControls, x402Client, x402ClientSync

from x402_openai._chains._types import EvmConfig, SvmConfig, TvmConfig
from x402_openai._client import AsyncX402OpenAI, X402OpenAI
from x402_openai._policies import prefer_network, prefer_scheme

__all__ = [
    "AsyncX402OpenAI",
    "EvmConfig",
    "SpendControls",
    "SvmConfig",
    "TvmConfig",
    "X402OpenAI",
    "prefer_network",
    "prefer_scheme",
    "x402Client",
    "x402ClientSync",
]
