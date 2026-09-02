"""TVM (TON) chat completion with private key.

Registers `exact` on `tvm:-239` by default. `close()` disposes ExactTvmScheme
HTTP clients. Close before the first request is a no-op.

Usage: TVM_PRIVATE_KEY="hex-or-base64..." python examples/chat_tvm.py
"""

import os

from x402_openai import X402OpenAI

client = X402OpenAI(tvm=os.environ["TVM_PRIVATE_KEY"])
try:
    response = client.chat.completions.create(
        model=os.environ.get("MODEL", "openai/gpt-4o-mini"),
        messages=[{"role": "user", "content": "What is the x402 payment protocol?"}],
    )
    print(response.choices[0].message.content)
finally:
    client.close()
