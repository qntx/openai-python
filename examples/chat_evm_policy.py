"""EVM chat completion with payment policy (prefer a network).

Usage: EVM_PRIVATE_KEY="0x..." python examples/chat_evm_policy.py
"""

import os

from qntx.openai import X402OpenAI, prefer_network

client = X402OpenAI(
    evm=os.environ["EVM_PRIVATE_KEY"],
    policies=[prefer_network("eip155:8453")],
)

response = client.chat.completions.create(
    model=os.environ.get("MODEL", "openai/gpt-4o-mini"),
    messages=[{"role": "user", "content": "What is the x402 payment protocol?"}],
)
print(response.choices[0].message.content)
