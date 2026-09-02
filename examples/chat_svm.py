"""SVM (Solana) chat completion with private key.

Usage: SOLANA_PRIVATE_KEY="base58..." python examples/chat_svm.py
"""

import os

from qntx.openai import X402OpenAI

client = X402OpenAI(svm=os.environ["SOLANA_PRIVATE_KEY"])

response = client.chat.completions.create(
    model=os.environ.get("MODEL", "openai/gpt-4o-mini"),
    messages=[{"role": "user", "content": "What is the x402 payment protocol?"}],
)
print(response.choices[0].message.content)
