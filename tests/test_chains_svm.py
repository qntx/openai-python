from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("solana.rpc.api")

from x402.mechanisms.svm.exact import ExactSvmScheme
from x402.schemas import PaymentRequired, PaymentRequirements, ResourceInfo

from x402_openai import prefer_scheme
from x402_openai._chains._register import register_chains
from x402_openai._chains._svm import register_svm
from x402_openai._chains._types import SvmConfig
from x402_openai._payments import PaymentSourceOptions, build_x402_client

# 64-byte Ed25519 secret (seed + pubkey), base58. Seed is 31 zero bytes + 0x01.
SVM_KEY = "1111111111111111111111111111111PPm2a2NNZH2EFJ5UkEjkH9Fcxn8cvjTmZDKQQisyLDmA"
SOLANA_MAINNET = "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def register(self, network: str, scheme: object) -> None:
        self.calls.append((network, scheme))


class _StubExact:
    scheme = "exact"

    def find_default_asset(
        self, asset: str, network: str | None = None
    ) -> dict[str, object] | None:
        return None

    def create_payment_payload(
        self, requirements: object, extensions: object = None
    ) -> dict[str, str]:
        return {"stub": "exact"}


def test_register_svm_registers_exact_only() -> None:
    client = _RecordingClient()
    register_svm(client, SvmConfig(private_key=SVM_KEY))  # type: ignore[arg-type]
    assert len(client.calls) == 1
    assert client.calls[0][0] == "solana:*"
    assert isinstance(client.calls[0][1], ExactSvmScheme)


def test_register_svm_with_rpc_url() -> None:
    client = _RecordingClient()
    register_svm(
        client,  # type: ignore[arg-type]
        SvmConfig(private_key=SVM_KEY, rpc_url="http://127.0.0.1:8899"),
    )
    scheme = client.calls[0][1]
    assert isinstance(scheme, ExactSvmScheme)
    assert scheme._custom_rpc_url == "http://127.0.0.1:8899"


def test_build_registers_exact_only_on_solana() -> None:
    built = build_x402_client(PaymentSourceOptions(svm=SVM_KEY), sync=True)
    core = built.http._client
    schemes: dict[str, Any] = core._schemes["solana:*"]
    assert isinstance(schemes["exact"], ExactSvmScheme)
    assert "upto" not in schemes
    built.dispose()


def test_build_normalizes_svm_config_object() -> None:
    built = build_x402_client(PaymentSourceOptions(svm=SvmConfig(private_key=SVM_KEY)), sync=True)
    core = built.http._client
    schemes: dict[str, Any] = core._schemes["solana:*"]
    assert isinstance(schemes["exact"], ExactSvmScheme)
    assert "upto" not in schemes


def test_register_chains_string_svm() -> None:
    client = _RecordingClient()
    handles = register_chains(
        client,  # type: ignore[arg-type]
        PaymentSourceOptions(svm=SVM_KEY),
    )
    assert len(client.calls) == 1
    handles.dispose()


def test_register_chains_evm_and_svm() -> None:
    pytest.importorskip("eth_account")
    evm_key = "0xac0974dac38f24671676c33098b7abf185c4d7b8d04844c06a56a24126c6dcbd"
    client = _RecordingClient()
    register_chains(
        client,  # type: ignore[arg-type]
        PaymentSourceOptions(evm=evm_key, svm=SVM_KEY),
    )
    networks = [network for network, _ in client.calls]
    assert networks.count("eip155:*") == 2
    assert networks.count("solana:*") == 1
    assert isinstance(client.calls[-1][1], ExactSvmScheme)


def test_dispose_is_noop_for_svm() -> None:
    built = build_x402_client(PaymentSourceOptions(svm=SVM_KEY), sync=True)
    built.dispose()
    built.dispose()


def test_prefer_scheme_upto_on_svm_only_pays_exact() -> None:
    built = build_x402_client(
        PaymentSourceOptions(
            svm=SVM_KEY,
            spend_controls=False,
            policies=[prefer_scheme("upto")],
        ),
        sync=True,
    )
    core = built.http._client
    schemes: dict[str, Any] = core._schemes["solana:*"]
    assert isinstance(schemes["exact"], ExactSvmScheme)
    assert "upto" not in schemes
    schemes["exact"] = _StubExact()

    def accept(scheme: str) -> PaymentRequirements:
        return PaymentRequirements(
            scheme=scheme,
            network=SOLANA_MAINNET,
            asset="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount="1000000",
            pay_to="11111111111111111111111111111111",
            max_timeout_seconds=300,
            extra={},
        )

    payload = core.create_payment_payload(
        PaymentRequired(
            x402_version=2,
            resource=ResourceInfo(url="https://example.com/resource"),
            accepts=[accept("upto"), accept("exact")],
        )
    )
    assert payload.accepted.scheme == "exact"
    assert payload.payload == {"stub": "exact"}
