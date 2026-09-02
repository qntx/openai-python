"""Chat completion preferring the `upto` scheme (EVM Permit2).

Supplying `evm` registers both `exact` and `upto`. The 402 `amount` is the
authorized maximum — the client signs that ceiling.

Usage: EVM_PRIVATE_KEY="0x..." python examples/chat_upto.py
"""

import os

from qntx.openai import X402OpenAI, prefer_scheme

client = X402OpenAI(
    evm=os.environ["EVM_PRIVATE_KEY"],
    policies=[prefer_scheme("upto")],
)

response = client.chat.completions.create(
    model=os.environ.get("MODEL", "openai/gpt-4o-mini"),
    messages=[{"role": "user", "content": "What is the x402 upto payment scheme?"}],
)
print(response.choices[0].message.content)
