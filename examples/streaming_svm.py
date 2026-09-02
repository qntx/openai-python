"""SVM (Solana) async streaming chat completion with private key.

Usage: SOLANA_PRIVATE_KEY="base58..." python examples/streaming_svm.py
"""

import asyncio
import os

from x402_openai import AsyncX402OpenAI


async def main() -> None:
    client = AsyncX402OpenAI(svm=os.environ["SOLANA_PRIVATE_KEY"])

    stream = await client.chat.completions.create(
        model=os.environ.get("MODEL", "openai/gpt-4o-mini"),
        messages=[{"role": "user", "content": "Explain the x402 payment protocol."}],
        stream=True,
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()


asyncio.run(main())
