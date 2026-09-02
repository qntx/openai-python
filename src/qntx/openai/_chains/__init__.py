"""Chain registration (EVM)."""

from __future__ import annotations

from qntx.openai._chains._register import ChainHandles, register_chains
from qntx.openai._chains._types import EvmConfig

__all__ = ["ChainHandles", "EvmConfig", "register_chains"]
