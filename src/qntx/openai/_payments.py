"""Assert constructor payment options and build the official x402 HTTP client."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, cast

from x402 import SpendControls, x402Client, x402ClientSync
from x402.http import x402HTTPClient, x402HTTPClientSync

from qntx.openai._chains._register import register_chains

if TYPE_CHECKING:
    from qntx.openai._chains._types import EvmConfig, SvmConfig

Policy = Callable[[int, list[Any]], list[Any]]
Selector = Callable[[int, list[Any]], Any]


PREBUILT_EXCLUSIVE = (
    "Cannot combine 'x402_client' with 'evm', 'svm', "
    "'policies', 'spend_controls', or 'payment_requirements_selector'. "
    "Configure the pre-built client directly."
)


@dataclass(frozen=True, slots=True)
class PaymentSourceOptions:
    evm: str | EvmConfig | None = None
    svm: str | SvmConfig | None = None
    spend_controls: SpendControls | Literal[False] | None = None
    policies: list[Policy] | None = None
    payment_requirements_selector: Selector | None = None
    x402_client: x402Client | x402ClientSync | None = None


class BuiltClient(NamedTuple):
    http: x402HTTPClientSync | x402HTTPClient
    dispose: Callable[[], None]


def assert_payment_options(options: PaymentSourceOptions) -> None:
    if options.x402_client is not None:
        if any(
            v is not None
            for v in (
                options.evm,
                options.svm,
                options.spend_controls,
                options.policies,
                options.payment_requirements_selector,
            )
        ):
            raise ValueError(PREBUILT_EXCLUSIVE)
        return
    if options.evm is None and options.svm is None:
        raise ValueError("Provide at least one of 'evm', 'svm', or 'x402_client'.")
    if options.evm is not None:
        _assert_non_empty_private_key("evm", options.evm)
    if options.svm is not None:
        _assert_non_empty_private_key("svm", options.svm)


def _assert_non_empty_private_key(field: str, value: str | EvmConfig | SvmConfig) -> None:
    key = value if isinstance(value, str) else value.private_key
    if not key:
        raise ValueError(f"'{field}' private key must be a non-empty string.")


def build_x402_client(options: PaymentSourceOptions, *, sync: bool) -> BuiltClient:
    assert_payment_options(options)
    if options.x402_client is not None:
        if sync:
            http: x402HTTPClientSync | x402HTTPClient = x402HTTPClientSync(
                cast("x402ClientSync", options.x402_client)
            )
        else:
            http = x402HTTPClient(cast("x402Client", options.x402_client))
        return BuiltClient(http=http, dispose=lambda: None)

    if sync:
        client: x402ClientSync | x402Client = x402ClientSync(options.payment_requirements_selector)
        if options.spend_controls is not None:
            client.set_spend_controls(options.spend_controls)
        handles = register_chains(client, options)
        for policy in options.policies or ():
            client.register_policy(policy)
        return BuiltClient(
            http=x402HTTPClientSync(cast("x402ClientSync", client)),
            dispose=handles.dispose,
        )

    client = x402Client(options.payment_requirements_selector)
    if options.spend_controls is not None:
        client.set_spend_controls(options.spend_controls)
    handles = register_chains(client, options)
    for policy in options.policies or ():
        client.register_policy(policy)
    return BuiltClient(
        http=x402HTTPClient(client),
        dispose=handles.dispose,
    )
