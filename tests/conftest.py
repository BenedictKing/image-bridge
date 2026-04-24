from __future__ import annotations

import os
from collections.abc import Iterable

import pytest


def _env_truthy(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


def _normalize_option(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _get_selection(config: pytest.Config) -> dict[str, str | None | bool]:
    return {
        "run_live": bool(config.getoption("--run-live")) or _env_truthy("IMAGE_BRIDGE_RUN_LIVE"),
        "live_case": _normalize_option(config.getoption("--live-case"))
        or _normalize_option(os.getenv("IMAGE_BRIDGE_LIVE_CASE")),
        "live_provider": _normalize_option(config.getoption("--live-provider"))
        or _normalize_option(os.getenv("IMAGE_BRIDGE_LIVE_PROVIDER")),
        "live_protocol": _normalize_option(config.getoption("--live-protocol"))
        or _normalize_option(os.getenv("IMAGE_BRIDGE_LIVE_PROTOCOL")),
        "live_capability": _normalize_option(config.getoption("--live-capability"))
        or _normalize_option(os.getenv("IMAGE_BRIDGE_LIVE_CAPABILITY")),
    }


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="run live tests that call real upstream provider APIs",
    )
    parser.addoption(
        "--live-case",
        action="store",
        default=None,
        help="run a single live case by stable case id",
    )
    parser.addoption(
        "--live-provider",
        action="store",
        default=None,
        help="filter live tests by provider",
    )
    parser.addoption(
        "--live-protocol",
        action="store",
        default=None,
        help="filter live tests by protocol",
    )
    parser.addoption(
        "--live-capability",
        action="store",
        default=None,
        help="filter live tests by capability",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: tests that call real upstream provider APIs")
    config.addinivalue_line("markers", "live_generate: live tests for generate_image")
    config.addinivalue_line("markers", "live_edit: live tests for edit_image")


def _matches_case_filter(item: pytest.Item, selected_value: str | None, key: str) -> bool:
    if selected_value is None:
        return True
    live_case = getattr(item, "callspec", None)
    if live_case is None:
        return False
    params = live_case.params
    case = params.get("live_case")
    if case is None:
        return False
    return getattr(case, key, None) == selected_value


def _iter_live_items(items: Iterable[pytest.Item]) -> tuple[list[pytest.Item], list[pytest.Item]]:
    live_items: list[pytest.Item] = []
    other_items: list[pytest.Item] = []
    for item in items:
        if item.get_closest_marker("live"):
            live_items.append(item)
        else:
            other_items.append(item)
    return live_items, other_items


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    selected = _get_selection(config)
    run_live = bool(selected["run_live"])
    live_case_id = selected["live_case"]
    live_provider = selected["live_provider"]
    live_protocol = selected["live_protocol"]
    live_capability = selected["live_capability"]

    live_items, other_items = _iter_live_items(items)
    if not live_items:
        return

    selected_live: list[pytest.Item] = []
    deselected: list[pytest.Item] = []

    for item in live_items:
        case_id = getattr(getattr(item, "callspec", None), "id", None)
        if not run_live:
            deselected.append(item)
            continue
        if live_case_id is not None and case_id != live_case_id:
            deselected.append(item)
            continue
        if not _matches_case_filter(item, live_provider, "provider"):
            deselected.append(item)
            continue
        if not _matches_case_filter(item, live_protocol, "protocol"):
            deselected.append(item)
            continue
        if not _matches_case_filter(item, live_capability, "capability"):
            deselected.append(item)
            continue
        selected_live.append(item)

    if live_case_id is not None and run_live and not selected_live:
        raise pytest.UsageError(f"No live test matched --live-case={live_case_id}")

    if deselected:
        config.hook.pytest_deselected(items=deselected)

    items[:] = [*other_items, *selected_live]
