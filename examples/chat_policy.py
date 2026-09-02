"""Chat completion with spend_controls and preference policies.

Caps each payment at $0.50 of a default asset, prefers Base, then `upto`.

Usage: EVM_PRIVATE_KEY="0x..." python examples/chat_policy.py
"""

import os

from qntx.openai import X402OpenAI, prefer_network, prefer_scheme

client = X402OpenAI(
    evm=os.environ["EVM_PRIVATE_KEY"],
    spend_controls={"max_amount_per_payment": "$0.50"},
    policies=[prefer_network("eip155:8453"), prefer_scheme("upto")],
)

response = client.chat.completions.create(
    model=os.environ.get("MODEL", "openai/gpt-4o-mini"),
    messages=[{"role": "user", "content": "What is the x402 payment protocol?"}],
)
print(response.choices[0].message.content)
