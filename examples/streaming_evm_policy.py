"""EVM async streaming chat completion with a network policy.

Usage: EVM_PRIVATE_KEY="0x..." python examples/streaming_evm_policy.py
"""

import asyncio
import os

from qntx.openai import AsyncX402OpenAI, prefer_network


async def main() -> None:
    client = AsyncX402OpenAI(
        evm=os.environ["EVM_PRIVATE_KEY"],
        policies=[prefer_network("eip155:8453")],
    )

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
