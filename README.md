<!-- markdownlint-disable MD033 MD041 MD036 -->

<div align="center">

# x402 OpenAI Python

**Drop-in OpenAI Python client with transparent [x402](https://www.x402.org/) payment support.**

[![PyPI](https://img.shields.io/pypi/v/x402-openai)](https://pypi.org/project/x402-openai/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![CI](https://github.com/qntx/x402-openai-python/actions/workflows/python.yml/badge.svg)](https://github.com/qntx/x402-openai-python/actions)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

---

Wrap the standard `openai.OpenAI` client with a crypto wallet.
When the server responds with **HTTP 402**, the library automatically signs and retries the request — zero code changes needed.

## Installation

```bash
pip install x402-openai[evm]          # Ethereum / Base / …
pip install x402-openai[svm]          # Solana
pip install x402-openai[all]          # all chains
```

## Quick Start

```python
from x402_openai import X402OpenAI
from x402_openai.wallets import EvmWallet

client = X402OpenAI(wallet=EvmWallet(private_key="0x…"))

res = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(res.choices[0].message.content)
```

Swap `EvmWallet` for `SvmWallet` to pay on Solana — the API is identical.

## Usage

### Async & Streaming

```python
from x402_openai import AsyncX402OpenAI

client = AsyncX402OpenAI(wallet=EvmWallet(private_key="0x…"))

stream = await client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Explain x402"}],
    stream=True,
)
async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Multi-chain

```python
from x402_openai.wallets import EvmWallet, SvmWallet

client = X402OpenAI(wallets=[
    EvmWallet(private_key="0x…"),
    SvmWallet(private_key="base58…"),
])
```

### BIP-39 Mnemonic (EVM)

```python
wallet = EvmWallet(mnemonic="word1 word2 … word12")
wallet = EvmWallet(mnemonic="…", account_index=2)                  # m/44'/60'/0'/0/2
wallet = EvmWallet(mnemonic="…", derivation_path="m/44'/60'/2'/0/0")  # custom path
```

The protocol selects the right chain automatically based on the server's payment requirements.

### Payment Policies

Use policies to control which chain or scheme is preferred when multiple payment options are available:

```python
from x402_openai import X402OpenAI, prefer_network, prefer_scheme, max_amount
from x402_openai.wallets import EvmWallet, SvmWallet

client = X402OpenAI(
    wallets=[
        EvmWallet(private_key="0x…"),
        SvmWallet(private_key="base58…"),
    ],
    policies=[
        prefer_network("eip155:8453"),  # Prefer Base mainnet
        prefer_scheme("exact"),         # Prefer exact payment scheme
        max_amount(1_000_000),          # Cap at 1 USDC (6 decimals)
    ],
)
```

## API Reference

### `X402OpenAI` / `AsyncX402OpenAI`

Drop-in replacement for `openai.OpenAI` / `openai.AsyncOpenAI`. Provide **exactly one** credential source:

| Parameter | Type | Description |
| :-- | :-- | :-- |
| `wallet` | `Wallet` | Single wallet adapter |
| `wallets` | `list[Wallet]` | Multiple adapters (multi-chain) |
| `policies` | `list[Policy]` | Payment policies (chain/scheme preference, amount cap) |
| `x402_client` | `x402HTTPClient*` | Pre-configured x402 client (bypasses `policies`) |

All standard OpenAI kwargs (`base_url`, `timeout`, `max_retries`, …) are forwarded.
Default `base_url`: `https://llm.qntx.org/v1`

### Wallet Adapters

| Class | Chain | Extra |
| :-- | :-- | :-- |
| `EvmWallet(private_key=…)` | EVM | `x402-openai[evm]` |
| `EvmWallet(mnemonic=…)` | EVM (BIP-39) | `x402-openai[evm]` |
| `SvmWallet(private_key=…)` | Solana | `x402-openai[svm]` |

Implement the [`Wallet`](src/x402_openai/wallets/_base.py) protocol to add a new chain.

### Low-level Transports

`X402Transport` / `AsyncX402Transport` — httpx transports for manual wiring into any `httpx.Client`.

## Examples

See the [`examples/`](examples/) directory. Each script is self-contained:

```bash
EVM_PRIVATE_KEY="0x…"           python examples/chat_evm.py
SOLANA_PRIVATE_KEY="base58…"    python examples/chat_svm.py
EVM_PRIVATE_KEY="0x…"           python examples/streaming_evm.py
MNEMONIC="word1 word2 …"       python examples/chat_evm_mnemonic.py
EVM_PRIVATE_KEY="0x…"           python examples/chat_evm_policy.py
EVM_PRIVATE_KEY="0x…"           python examples/streaming_evm_policy.py
```

## License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

A **[QuantX](https://qntx.org)** open-source project.

<a href="https://qntx.org"><img alt="QuantX" width="369" src="https://raw.githubusercontent.com/qntx/.github/main/profile/qntx.svg" /></a>

Code is law. We write both.

</div>
