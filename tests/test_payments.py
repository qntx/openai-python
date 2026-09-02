from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from x402 import x402Client, x402ClientSync
from x402.http import x402HTTPClient, x402HTTPClientSync
from x402.schemas import PaymentRequired, PaymentRequirements, ResourceInfo

from x402_openai._chains._register import ChainHandles
from x402_openai._chains._types import EvmConfig, SvmConfig, TvmConfig
from x402_openai._payments import (
    PREBUILT_EXCLUSIVE,
    PaymentSourceOptions,
    assert_payment_options,
    build_x402_client,
)

EVM_KEY = "0xac0974dac38f24671676c33098b7abf185c4d7b8d04844c06a56a24126c6dcbd"
TVM_KEY = "11" * 32
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


class StubUsdcScheme:
    def __init__(self, scheme: str) -> None:
        self.scheme = scheme

    def find_default_asset(
        self, asset: str, network: str | None = None
    ) -> dict[str, object] | None:
        if asset.lower() == BASE_USDC.lower():
            return {"asset": BASE_USDC, "decimals": 6, "symbol": "USDC"}
        return None

    def create_payment_payload(
        self, requirements: object, extensions: object = None
    ) -> dict[str, str]:
        return {"stub": self.scheme}


def usdc_accept(amount: str, scheme: str) -> PaymentRequirements:
    return PaymentRequirements(
        scheme=scheme,
        network="eip155:8453",
        asset=BASE_USDC,
        amount=amount,
        pay_to="0x0000000000000000000000000000000000000001",
        max_timeout_seconds=300,
        extra={},
    )


def usdc_required(amount: str, scheme: str = "exact") -> PaymentRequired:
    return PaymentRequired(
        x402_version=2,
        resource=ResourceInfo(url="https://example.com/resource"),
        accepts=[usdc_accept(amount, scheme)],
    )


def _noop_register(client: object, options: object) -> ChainHandles:
    return ChainHandles()


def test_assert_throws_when_no_credentials() -> None:
    with pytest.raises(ValueError, match=r"'evm', 'svm', 'tvm', or 'x402_client'"):
        assert_payment_options(PaymentSourceOptions())


def test_assert_throws_on_empty_evm() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        assert_payment_options(PaymentSourceOptions(evm=""))


def test_assert_throws_on_empty_evm_config() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        assert_payment_options(PaymentSourceOptions(evm=EvmConfig(private_key="")))


def test_assert_throws_on_empty_svm() -> None:
    with pytest.raises(ValueError, match="'svm' private key must be a non-empty string"):
        assert_payment_options(PaymentSourceOptions(svm=""))


def test_assert_throws_on_empty_svm_config() -> None:
    with pytest.raises(ValueError, match="'svm' private key must be a non-empty string"):
        assert_payment_options(PaymentSourceOptions(svm=SvmConfig(private_key="")))


def test_assert_svm_only_ok() -> None:
    assert_payment_options(PaymentSourceOptions(svm="base58"))


def test_assert_throws_on_empty_tvm() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        assert_payment_options(PaymentSourceOptions(tvm=""))


def test_assert_throws_on_empty_tvm_config() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        assert_payment_options(PaymentSourceOptions(tvm=TvmConfig(private_key="")))


def test_assert_accepts_tvm_without_evm() -> None:
    assert_payment_options(PaymentSourceOptions(tvm=TVM_KEY))


def test_assert_prebuilt_exclusive_keys() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        assert_payment_options(PaymentSourceOptions(x402_client=x402ClientSync(), evm=EVM_KEY))


def test_assert_prebuilt_exclusive_svm() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        assert_payment_options(PaymentSourceOptions(x402_client=x402ClientSync(), svm="base58"))


def test_assert_prebuilt_exclusive_tvm() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        assert_payment_options(PaymentSourceOptions(x402_client=x402ClientSync(), tvm=TVM_KEY))


def test_assert_prebuilt_exclusive_policies() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        assert_payment_options(
            PaymentSourceOptions(x402_client=x402ClientSync(), policies=[lambda _v, reqs: reqs])
        )


def test_assert_prebuilt_exclusive_spend_controls_false() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        assert_payment_options(
            PaymentSourceOptions(x402_client=x402ClientSync(), spend_controls=False)
        )


def test_assert_prebuilt_exclusive_selector() -> None:
    with pytest.raises(ValueError, match="Cannot combine"):
        assert_payment_options(
            PaymentSourceOptions(
                x402_client=x402ClientSync(),
                payment_requirements_selector=lambda _v, reqs: reqs[0],
            )
        )


def test_prebuilt_exclusive_message() -> None:
    assert "x402_client" in PREBUILT_EXCLUSIVE
    assert "evm" in PREBUILT_EXCLUSIVE
    assert "svm" in PREBUILT_EXCLUSIVE
    assert "tvm" in PREBUILT_EXCLUSIVE


def test_build_returns_prebuilt_wrapped() -> None:
    prebuilt = x402ClientSync()
    result = build_x402_client(PaymentSourceOptions(x402_client=prebuilt), sync=True)
    assert isinstance(result.http, x402HTTPClientSync)
    assert result.http._client is prebuilt
    result.dispose()


def test_build_async_prebuilt_wrapped() -> None:
    prebuilt = x402Client()
    result = build_x402_client(PaymentSourceOptions(x402_client=prebuilt), sync=False)
    assert isinstance(result.http, x402HTTPClient)
    assert result.http._client is prebuilt


def test_build_does_not_call_set_spend_controls_when_omitted() -> None:
    calls: list[object] = []

    class _Client(x402ClientSync):
        def set_spend_controls(self, controls: object) -> Any:
            calls.append(controls)
            return super().set_spend_controls(controls)  # type: ignore[misc]

    with (
        patch("x402_openai._payments.x402ClientSync", _Client),
        patch("x402_openai._payments.register_chains", _noop_register),
    ):
        build_x402_client(PaymentSourceOptions(evm=EVM_KEY), sync=True)
    assert calls == []


def test_build_set_spend_controls_false() -> None:
    calls: list[object] = []

    class _Client(x402ClientSync):
        def set_spend_controls(self, controls: object) -> Any:
            calls.append(controls)
            return super().set_spend_controls(controls)  # type: ignore[misc]

    with (
        patch("x402_openai._payments.x402ClientSync", _Client),
        patch("x402_openai._payments.register_chains", _noop_register),
    ):
        build_x402_client(PaymentSourceOptions(evm=EVM_KEY, spend_controls=False), sync=True)
    assert calls == [False]


def _core(built: object) -> x402ClientSync:
    http = built.http  # type: ignore[attr-defined]
    return http._client


def test_spend_controls_omitted_rejects_2_usdc() -> None:
    with patch("x402_openai._payments.register_chains", _noop_register):
        built = build_x402_client(PaymentSourceOptions(evm=EVM_KEY), sync=True)
    core = _core(built)
    core.register("eip155:8453", StubUsdcScheme("exact"))
    with pytest.raises(Exception, match="max_amount_per_payment"):
        core.create_payment_payload(usdc_required("2000000"))


def test_spend_controls_explicit_1_rejects_2_usdc() -> None:
    with patch("x402_openai._payments.register_chains", _noop_register):
        built = build_x402_client(
            PaymentSourceOptions(evm=EVM_KEY, spend_controls={"max_amount_per_payment": "$1"}),
            sync=True,
        )
    core = _core(built)
    core.register("eip155:8453", StubUsdcScheme("exact"))
    with pytest.raises(Exception, match="max_amount_per_payment"):
        core.create_payment_payload(usdc_required("2000000"))


def test_spend_controls_5_allows_2_usdc() -> None:
    with patch("x402_openai._payments.register_chains", _noop_register):
        built = build_x402_client(
            PaymentSourceOptions(evm=EVM_KEY, spend_controls={"max_amount_per_payment": "$5"}),
            sync=True,
        )
    core = _core(built)
    core.register("eip155:8453", StubUsdcScheme("exact"))
    payload = core.create_payment_payload(usdc_required("2000000"))
    assert payload.payload == {"stub": "exact"}


def test_spend_controls_false_allows_2_usdc() -> None:
    with patch("x402_openai._payments.register_chains", _noop_register):
        built = build_x402_client(
            PaymentSourceOptions(evm=EVM_KEY, spend_controls=False), sync=True
        )
    core = _core(built)
    core.register("eip155:8453", StubUsdcScheme("exact"))
    payload = core.create_payment_payload(usdc_required("2000000"))
    assert payload.payload == {"stub": "exact"}


def test_build_registers_policies() -> None:
    from x402_openai import prefer_scheme

    policy = prefer_scheme("upto")
    with patch("x402_openai._payments.register_chains", _noop_register):
        built = build_x402_client(
            PaymentSourceOptions(evm=EVM_KEY, policies=[policy]),
            sync=True,
        )
    core = _core(built)
    assert policy in core._policies


def test_selector_runs_after_spend_controls() -> None:
    with patch("x402_openai._payments.register_chains", _noop_register):
        built = build_x402_client(
            PaymentSourceOptions(
                evm=EVM_KEY,
                spend_controls=False,
                payment_requirements_selector=lambda _version, reqs: reqs[1],
            ),
            sync=True,
        )
    core = _core(built)
    core.register("eip155:8453", StubUsdcScheme("exact"))
    payload = core.create_payment_payload(
        PaymentRequired(
            x402_version=2,
            resource=ResourceInfo(url="https://example.com/resource"),
            accepts=[usdc_accept("100000", "exact"), usdc_accept("200000", "exact")],
        )
    )
    assert payload.accepted.amount == "200000"
