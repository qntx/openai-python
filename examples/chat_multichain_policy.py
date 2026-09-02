"""Multi-chain chat completion with payment policies.

Registers both EVM and SVM keys, then prefers Base and the `upto` scheme.
`prefer_scheme("upto")` only filters EVM (`upto` is registered there). SVM
pays `exact` only. Official spend controls stay at `$1` (omit `spend_controls`).

Usage:
  EVM_PRIVATE_KEY="0x..." SOLANA_PRIVATE_KEY="base58..." \
    python examples/chat_multichain_policy.py
"""

import os

from x402_openai import X402OpenAI, prefer_network, prefer_scheme

client = X402OpenAI(
    evm=os.environ["EVM_PRIVATE_KEY"],
    svm=os.environ["SOLANA_PRIVATE_KEY"],
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
