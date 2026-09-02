<!-- markdownlint-disable MD033 MD041 MD036 -->

<div align="center">

# qntx-openai

**Drop-in OpenAI Python client with transparent [x402](https://www.x402.org/) payment support.**

[![PyPI](https://img.shields.io/pypi/v/qntx-openai)](https://pypi.org/project/qntx-openai/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![CI](https://github.com/qntx/openai-python/actions/workflows/python.yml/badge.svg)](https://github.com/qntx/openai-python/actions)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

---

Wrap the standard `openai.OpenAI` client with per-chain private keys.
When the server responds with **HTTP 402**, the library automatically signs and retries the request — zero code changes needed.

Supplying `evm` registers both **`exact` and `upto`**. `svm` and `tvm` register **`exact` only**. Default spend controls from `x402` cap each payment at **`$1`** of a recognized default asset.

## Installation

```bash
pip install 'qntx-openai[evm]'          # EVM (Ethereum / Base / …)
pip install 'qntx-openai[svm]'          # Solana
pip install 'qntx-openai[tvm]'          # TVM (TON)
pip install 'qntx-openai[all]'          # all chains
```

The PyPI name `x402-openai` is abandoned. Install `qntx-openai`.

## Quick Start

```python
from qntx.openai import X402OpenAI

client = X402OpenAI(evm="0x…")

res = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(res.choices[0].message.content)
```

Pass `svm="base58…"` instead of `evm` to pay on Solana — the rest of the API is identical. The same constructor accepts `tvm`.

## Usage

### Streaming

```python
from qntx.openai import AsyncX402OpenAI

client = AsyncX402OpenAI(evm="0x…")

stream = await client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Explain x402"}],
    stream=True,
)

async for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="")
```

### Multi-chain

```python
client = X402OpenAI(
    evm="0x…",
    svm="base58…",
    tvm="hex-or-base64…",
)
```

The protocol selects the right chain automatically based on the server's payment requirements.

### Key formats

| Option | Key material |
| :----- | :----------- |
| `evm`  | `0x` hex secp256k1 |
| `svm`  | base58 64-byte secret |
| `tvm`  | hex/base64 32-byte seed or 64-byte secret |

Bare `evm` / `svm` / `tvm` strings become `{ private_key }`. Empty strings throw. Config objects are `EvmConfig` / `SvmConfig` (`private_key`, optional `rpc_url`) and `TvmConfig` (`private_key`, optional `network` / `provider` / `api_key` / `provider_base_url`).

### TVM

TVM registers **`exact` only** on a **concrete CAIP-2**. Default network is **`tvm:-239`** (or pass `network="tvm:-3"`). The client never registers `tvm:*` — the signer is bound to one network.

- Hex/base64 32-byte seed or 64-byte secret, or `TvmConfig(private_key, network?, provider?, api_key?, provider_base_url?)`.
- The 402 **must** set `extra.areFeesSponsored is True`.
- Default asset is USDT jetton; native TON is not a default asset — pass `spend_controls.allowed_assets` to allow it.

Long-lived TVM clients hold `ExactTvmScheme` HTTP clients. Call `client.close()` (sync) or `await client.aclose()` (async) when finished. `close()` before the first request is a no-op. A request after `close()` raises `X402OpenAI is closed` and does not rebuild.

### Spend controls

`x402Client()` / `x402ClientSync()` already allow only default (USD-pegged) assets and cap each payment at **`$1`**. This package does not change that default.

Pass `spend_controls` to raise the cap, allow extra assets, or disable controls:

```python
client = X402OpenAI(
    evm="0x…",
    spend_controls={"max_amount_per_payment": "$5"},
)
```

- Omit `spend_controls` to keep the official `$1` + default-asset allowlist.
- `spend_controls=False` disables allowlist and caps.
- Gateway prices above `$1` require the caller to raise `max_amount_per_payment`.

### `exact` and `upto`

`evm` registers `ExactEvmScheme` and `UptoEvmScheme` on `eip155:*`. `svm` registers `ExactSvmScheme` on `solana:*` (**no Python `upto`**). `tvm` registers `ExactTvmScheme` on the configured CAIP-2. No extra flag; the gateway is not probed.

- **EVM `upto`:** Permit2 (`permitWitnessTransferFrom`). The 402 must include `extra.facilitatorAddress`. Pass `{ rpc_url }` on `evm` to enable official EIP-2612 / ERC-20 approval sponsoring.
- **SVM `exact`:** the 402 must include `extra.feePayer`. There is no SVM `upto` scheme in Python `x402`.
- The 402 `amount` is the **authorized maximum**. The client signs that max; it does not sign a smaller amount. The server chooses the actual charge (`<=` max) at settle. If the ceiling exceeds spend controls, payment creation throws.

```python
from qntx.openai import X402OpenAI, prefer_scheme

client = X402OpenAI(
    evm="0x…",
    policies=[prefer_scheme("upto")],
)
```

`prefer_scheme("upto")` only affects chains that registered `upto` (EVM). An SVM-only client still pays `exact`.

### Payment Policies

Use policies to prefer a chain or scheme when multiple options remain after spend controls. Policies do not cap spend.

```python
from qntx.openai import X402OpenAI, prefer_network, prefer_scheme

client = X402OpenAI(
    evm="0x…",
    svm="base58…",
    policies=[
        prefer_network("eip155:8453"),  # Prefer Base mainnet
        prefer_scheme("upto"),
    ],
)
```

If nothing matches, all remaining options pass through. On this client, `prefer_scheme("upto")` filters EVM requirements; SVM still pays `exact`.

### Closing

```python
client.close()          # X402OpenAI
await client.aclose()   # AsyncX402OpenAI
```

`close()` / `aclose()` dispose TVM `ExactTvmScheme` HTTP clients. Close before the first request is a no-op. A request after close raises `X402OpenAI is closed` and does not rebuild.

## API Reference

### `X402OpenAI` / `AsyncX402OpenAI`

Drop-in replacement for `openai.OpenAI` / `openai.AsyncOpenAI`. Provide **at least one** of `evm`, `svm`, `tvm`, or `x402_client`:

| Parameter | Type | Description |
| :-------- | :--- | :---------- |
| `evm` | `str` or `EvmConfig` | EVM secp256k1 private key (`0x` hex). Registers `exact` and `upto` on `eip155:*`. |
| `svm` | `str` or `SvmConfig` | Solana base58 secret key. Registers `exact` only on `solana:*`. |
| `tvm` | `str` or `TvmConfig` | TON seed/secret. Registers `exact` on `tvm:-239` by default (`tvm:-3` if set). Never `tvm:*`. |
| `spend_controls` | `SpendControls` or `False` | Official spend controls. Omit for `$1` + default assets. |
| `policies` | `list[Policy]` | Preference policies (`prefer_network` / `prefer_scheme`). |
| `payment_requirements_selector` | `Selector` | Picks among remaining requirements after spend controls and policies. |
| `x402_client` | `x402ClientSync` / `x402Client` | Pre-configured **core** x402 client (exclusive with keys, spend_controls, policies, payment_requirements_selector). |

| Type | Fields | Notes |
| :--- | :----- | :---- |
| `EvmConfig` | `{ private_key, rpc_url? }` | `rpc_url` enables EIP-2612 / ERC-20 approval sponsoring |
| `SvmConfig` | `{ private_key, rpc_url? }` | `rpc_url` is Solana JSON-RPC |
| `TvmConfig` | `{ private_key, network?, provider?, api_key?, provider_base_url? }` | `network` is `tvm:-239` or `tvm:-3` |

Empty keys throw.

`close()` / `aclose()` release TVM handles. Close before the first request is a no-op. A request after close raises `X402OpenAI is closed` and does not rebuild.

`SpendControls` is the official snake_case TypedDict from `x402`.

All standard OpenAI options (`base_url`, `timeout`, `max_retries`, …) are forwarded. Default `base_url`: `https://llm.qntx.org/v1`. `api_key` defaults to `"x402"`. `http_client` is not accepted.

| Option | Chain | Install extra |
| :----- | :---- | :------------ |
| `evm` | EVM | `qntx-openai[evm]` |
| `svm` | Solana | `qntx-openai[svm]` |
| `tvm` | TVM | `qntx-openai[tvm]` |

## Examples

See the [`examples/`](examples/) directory. Each script is self-contained:

```bash
EVM_PRIVATE_KEY="0x…"           python examples/chat_evm.py
SOLANA_PRIVATE_KEY="base58…"    python examples/chat_svm.py
TVM_PRIVATE_KEY="hex-or-base64…" python examples/chat_tvm.py
EVM_PRIVATE_KEY="0x…"           python examples/streaming_evm.py
SOLANA_PRIVATE_KEY="base58…"    python examples/streaming_svm.py
EVM_PRIVATE_KEY="0x…"           python examples/streaming_evm_policy.py
EVM_PRIVATE_KEY="0x…"           python examples/chat_upto.py
EVM_PRIVATE_KEY="0x…"           python examples/chat_policy.py
EVM_PRIVATE_KEY="0x…"           python examples/chat_evm_policy.py
EVM_PRIVATE_KEY="0x…"           python examples/models.py
EVM_PRIVATE_KEY="0x…" SOLANA_PRIVATE_KEY="base58…" python examples/chat_multichain_policy.py
```

## License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

A **[QuantX](https://qntx.org)** open-source project.

<a href="https://qntx.org"><img alt="QuantX" width="369" src="https://raw.githubusercontent.com/qntx/.github/main/profile/qntx.svg" /></a>

Code is law. We write both.

</div>
