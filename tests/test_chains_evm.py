from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("eth_account")

from x402.mechanisms.evm.exact import ExactEvmScheme
from x402.mechanisms.evm.signers import EthAccountSignerWithRPC
from x402.mechanisms.evm.upto import UptoEvmScheme

from x402_openai._chains._evm import register_evm
from x402_openai._chains._register import register_chains
from x402_openai._chains._types import EvmConfig
from x402_openai._payments import PaymentSourceOptions, build_x402_client

EVM_KEY = "0xac0974dac38f24671676c33098b7abf185c4d7b8d04844c06a56a24126c6dcbd"


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def register(self, network: str, scheme: object) -> None:
        self.calls.append((network, scheme))


def test_register_evm_registers_exact_and_upto() -> None:
    client = _RecordingClient()
    register_evm(client, EvmConfig(private_key=EVM_KEY))  # type: ignore[arg-type]
    assert len(client.calls) == 2
    assert client.calls[0][0] == "eip155:*"
    assert isinstance(client.calls[0][1], ExactEvmScheme)
    assert client.calls[1][0] == "eip155:*"
    assert isinstance(client.calls[1][1], UptoEvmScheme)


def test_register_evm_with_rpc_url_uses_rpc_signer() -> None:
    client = _RecordingClient()
    register_evm(
        client,  # type: ignore[arg-type]
        EvmConfig(private_key=EVM_KEY, rpc_url="http://127.0.0.1:8545"),
    )
    scheme = client.calls[0][1]
    assert isinstance(scheme._signer, EthAccountSignerWithRPC)  # type: ignore[attr-defined]


def test_build_registers_both_scheme_names_on_eip155() -> None:
    built = build_x402_client(PaymentSourceOptions(evm=EVM_KEY), sync=True)
    core = built.http._client
    schemes: dict[str, Any] = core._schemes["eip155:*"]
    assert isinstance(schemes["exact"], ExactEvmScheme)
    assert isinstance(schemes["upto"], UptoEvmScheme)
    built.dispose()


def test_build_normalizes_evm_config_object() -> None:
    built = build_x402_client(PaymentSourceOptions(evm=EvmConfig(private_key=EVM_KEY)), sync=True)
    core = built.http._client
    schemes: dict[str, Any] = core._schemes["eip155:*"]
    assert isinstance(schemes["exact"], ExactEvmScheme)
    assert isinstance(schemes["upto"], UptoEvmScheme)


def test_register_chains_string_evm() -> None:
    client = _RecordingClient()
    handles = register_chains(
        client,  # type: ignore[arg-type]
        PaymentSourceOptions(evm=EVM_KEY),
    )
    assert len(client.calls) == 2
    handles.dispose()


def test_dispose_is_noop_for_evm() -> None:
    built = build_x402_client(PaymentSourceOptions(evm=EVM_KEY), sync=True)
    built.dispose()
    built.dispose()
