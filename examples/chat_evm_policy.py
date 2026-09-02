"""EVM chat completion with payment policies.

Prefers Base mainnet, then the `upto` scheme.

Usage: EVM_PRIVATE_KEY="0x..." python examples/chat_evm_policy.py
"""

import os

from x402_openai import X402OpenAI, prefer_network, prefer_scheme

client = X402OpenAI(
    evm=os.environ["EVM_PRIVATE_KEY"],
    policies=[
        prefer_network("eip155:8453"),  # Prefer Base mainnet
        prefer_scheme("upto"),
    ],
)

response = client.chat.completions.create(
    model=os.environ.get("MODEL", "openai/gpt-4o-mini"),
    messages=[{"role": "user", "content": "What is the x402 payment protocol?"}],
)
print(response.choices[0].message.content)
