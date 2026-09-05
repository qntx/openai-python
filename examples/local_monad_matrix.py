"""Exercise exact + upto on Monad mainnet and testnet against local o402.

Usage: python examples/local_monad_matrix.py
"""

from __future__ import annotations

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

key = os.environ["EVM_PRIVATE_KEY"]
base_url = os.environ.get("O402_BASE_URL", "http://127.0.0.1:8080/v1")
chat_model = os.environ.get("MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct")
networks = ("eip155:143", "eip155:10143")


def rpc_url(network: str) -> str:
    return (
        "https://testnet-rpc.monad.xyz"
        if network == "eip155:10143"
        else "https://rpc.monad.xyz"
    )


def make_client(network: str, scheme: str) -> X402OpenAI:
    return X402OpenAI(
        evm=EvmConfig(private_key=key, rpc_url=rpc_url(network)),
        base_url=base_url,
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
        policies=[prefer_network(network), prefer_scheme(scheme)],
    )


unpaid = X402OpenAI(evm=key, base_url=base_url, api_key="x402", max_retries=0)
print("models", [model.id for model in unpaid.models.list().data[:12]])

for network in networks:
    try:
        chat = make_client(network, "upto").chat.completions.create(
            model=chat_model,
            messages=[{"role": "user", "content": f"One word for {network}"}],
            max_tokens=8,
            stream=False,
        )
        print("upto ok", {"network": network, "content": chat.choices[0].message.content})
    except Exception as exc:  # noqa: BLE001
        print("upto fail", network, type(exc).__name__, exc)

    try:
        image = make_client(network, "exact").images.generate(
            model="exact-echo",
            prompt=f"exact {network}",
            n=1,
            size="256x256",
        )
        url = None if not image.data else image.data[0].url
        print("exact ok", {"network": network, "url": url})
    except Exception as exc:  # noqa: BLE001
        print("exact fail", network, type(exc).__name__, exc)
