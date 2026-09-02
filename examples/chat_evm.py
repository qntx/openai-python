"""EVM chat completion with private key.

Usage: EVM_PRIVATE_KEY="0x..." python examples/chat_evm.py
"""

import os

from x402_openai import X402OpenAI

client = X402OpenAI(evm=os.environ["EVM_PRIVATE_KEY"])

response = client.chat.completions.create(
    model=os.environ.get("MODEL", "openai/gpt-4o-mini"),
    messages=[{"role": "user", "content": "What is the x402 payment protocol?"}],
)
print(response.choices[0].message.content)
