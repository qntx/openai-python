"""Local o402 exact settlement on Monad (mainnet or testnet).

Hits POST /v1/images/generations (o402 bills that path exact) against the
local echo upstream (`exact-echo`).

Usage:
  python examples/local_monad_exact.py
  NETWORK=eip155:10143 python examples/local_monad_exact.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _load_dotenv() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key, value)


_load_dotenv()
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost,::1")
os.environ.setdefault("no_proxy", os.environ["NO_PROXY"])

from x402_openai import EvmConfig, X402OpenAI, prefer_network, prefer_scheme

network = os.environ.get("NETWORK", "eip155:143")
rpc_url = (
    "https://testnet-rpc.monad.xyz"
    if network == "eip155:10143"
    else "https://rpc.monad.xyz"
)
client = X402OpenAI(
    evm=EvmConfig(private_key=os.environ["EVM_PRIVATE_KEY"], rpc_url=rpc_url),
    base_url=os.environ.get("O402_BASE_URL", "http://127.0.0.1:8080/v1"),
    api_key="x402",
    max_retries=0,
    spend_controls={
        "max_amount_per_payment": "$1",
        "allowed_assets": [
            {
                "network": "eip155:10143",
                "asset": "0x534b2f3A21130d7a60830c2Df862319e593943A3",
            }
        ],
    },
    policies=[prefer_network(network), prefer_scheme("exact")],
)

image = client.images.generate(
    model="exact-echo",
    prompt=f"exact {network}",
    n=1,
    size="256x256",
)
print(
    json.dumps(
        {
            "network": network,
            "model": "exact-echo",
            "scheme": "exact",
            "created": image.created,
            "url": None if not image.data else image.data[0].url,
        },
        indent=2,
    )
)
