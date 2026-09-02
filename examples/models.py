"""List available models from the x402 gateway.

Usage: EVM_PRIVATE_KEY="0x..." python examples/models.py
"""

import os

from qntx.openai import X402OpenAI

client = X402OpenAI(evm=os.environ["EVM_PRIVATE_KEY"])

for m in client.models.list():
    print(m.id)
