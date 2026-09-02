"""Chain registration (EVM, SVM)."""

from __future__ import annotations

from qntx.openai._chains._register import ChainHandles, register_chains
from qntx.openai._chains._types import EvmConfig, SvmConfig

__all__ = ["ChainHandles", "EvmConfig", "SvmConfig", "register_chains"]
