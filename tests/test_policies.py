from __future__ import annotations

from typing import Any, NamedTuple

from qntx.openai import prefer_network, prefer_scheme


class _Req(NamedTuple):
    network: str
    scheme: str
    amount: str = "100"


reqs: list[Any] = [
    _Req(network="eip155:8453", scheme="exact"),
    _Req(network="solana:mainnet", scheme="exact"),
]


def test_prefer_network_filters_matching() -> None:
    result = prefer_network("eip155:8453")(2, reqs)
    assert len(result) == 1
    assert result[0].network == "eip155:8453"


def test_prefer_network_wildcard_matches_prefix() -> None:
    all_reqs: list[Any] = [
        _Req(network="eip155:8453", scheme="exact"),
        _Req(network="eip155:1", scheme="exact"),
        _Req(network="solana:mainnet", scheme="exact"),
    ]
    result = prefer_network("eip155:*")(2, all_reqs)
    assert len(result) == 2


def test_prefer_network_passthrough_when_none_match() -> None:
    only_svm: list[Any] = [_Req(network="solana:mainnet", scheme="exact")]
    result = prefer_network("eip155:8453")(2, only_svm)
    assert len(result) == 1


def test_prefer_scheme_filters_matching() -> None:
    mixed: list[Any] = [
        _Req(network="eip155:8453", scheme="exact"),
        _Req(network="eip155:8453", scheme="streaming"),
    ]
    result = prefer_scheme("exact")(2, mixed)
    assert len(result) == 1
    assert result[0].scheme == "exact"


def test_prefer_scheme_prefers_upto_when_mixed_with_exact() -> None:
    mixed: list[Any] = [
        _Req(network="eip155:8453", scheme="exact"),
        _Req(network="eip155:8453", scheme="upto"),
    ]
    result = prefer_scheme("upto")(2, mixed)
    assert len(result) == 1
    assert result[0].scheme == "upto"


def test_prefer_scheme_passthrough_when_none_match() -> None:
    result = prefer_scheme("upto")(2, reqs)
    assert len(result) == 2
