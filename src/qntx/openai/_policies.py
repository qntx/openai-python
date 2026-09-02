"""Filter-or-passthrough payment policies (TS product semantics, not x402 reorder)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qntx.openai._payments import Policy


def prefer_network(network: str) -> Policy:
    """Keep requirements matching ``network``. ``eip155:*`` is prefix ``eip155:``.

    If nothing matches, return the original list so payment can still proceed.
    """
    is_wildcard = network.endswith(":*")
    prefix = network[:-1] if is_wildcard else None  # "eip155:"

    def policy(_version: int, reqs: list[Any]) -> list[Any]:
        matched = [
            r for r in reqs if (r.network.startswith(prefix) if prefix else r.network == network)
        ]
        return matched if matched else reqs

    return policy


def prefer_scheme(scheme: str) -> Policy:
    """Keep requirements matching ``scheme``; passthrough if none match."""

    def policy(_version: int, reqs: list[Any]) -> list[Any]:
        matched = [r for r in reqs if r.scheme == scheme]
        return matched if matched else reqs

    return policy
