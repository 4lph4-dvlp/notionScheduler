"""Require honest, complete evidence before claiming an API/MCP comparison."""

from copy import deepcopy

import pytest

from benchmarks.compare import validate_report


def report():
    return {
        "schema_version": 1,
        "access_context": "Controlled test connection",
        "measurements": [
            {
                "transport": transport,
                "operation": operation,
                "status": "approval_required" if operation != "read" else "unavailable",
                "sample_size": None,
                "tool_calls": None,
                "elapsed_ms": None,
                "returned_bytes": None,
                "model_tokens": None,
                "model_token_source": "unavailable",
                "metric_source": "Pending measurement method",
                "evidence": "Pending live observation",
            }
            for transport in ("api", "mcp")
            for operation in ("read", "create", "update")
        ],
    }


def test_complete_pending_report_is_valid():
    validate_report(report())


@pytest.mark.parametrize("missing", ["status", "sample_size", "tool_calls", "elapsed_ms", "returned_bytes", "model_tokens", "model_token_source", "metric_source", "evidence"])
def test_missing_metric_or_status_is_rejected(missing):
    data = report()
    del data["measurements"][0][missing]
    with pytest.raises(ValueError):
        validate_report(data)


def test_missing_workload_is_rejected():
    data = report()
    data["measurements"].pop()
    with pytest.raises(ValueError, match="Missing"):
        validate_report(data)


def test_measured_write_requires_real_evidence():
    data = report()
    entry = data["measurements"][1]
    entry.update(status="measured", sample_size=1, tool_calls=1, elapsed_ms=100, returned_bytes=100)
    data["cleanup"] = {"database_id": "temporary", "in_trash": True, "evidence": "independent retrieve"}
    with pytest.raises(ValueError, match="approval"):
        validate_report(data)
    entry.update(approval="user approval", disposable_target="test source", write_evidence="created page ID")
    validate_report(data)
    del data["cleanup"]
    with pytest.raises(ValueError, match="cleanup"):
        validate_report(data)


def test_character_count_cannot_masquerade_as_model_tokens():
    data = deepcopy(report())
    data["measurements"][0]["model_tokens"] = 123
    data["measurements"][0]["model_token_source"] = "unavailable"
    with pytest.raises(ValueError):
        validate_report(data)
