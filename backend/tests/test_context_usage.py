"""The context meter's numbers.

The meter shows what a turn's context is spent on, so the split has to be
measured rather than estimated, and an unmeasurable turn has to report
nothing at all — a zeroed meter reads as an empty context, which is a
different claim from "not measured".
"""
import angela
import pytest


class _Usage:
    def __init__(self, **fields):
        for name, value in fields.items():
            setattr(self, name, value)


class _Resp:
    def __init__(self, usage=None):
        self.usage = usage


class _Counter:
    """Counts a fixed cost per component, and records every call."""

    def __init__(self, system=500, tools=3000, probe=8):
        self.system, self.tools, self.probe = system, tools, probe
        self.calls = 0
        self.messages = self

    def count_tokens(self, *, model, messages, system=None, tools=None):
        self.calls += 1
        total = self.probe
        if system is not None:
            total += self.system
        if tools:
            total += self.tools
        return _Usage(input_tokens=total)


@pytest.fixture(autouse=True)
def _clear_cache():
    angela._PREFIX_TOKENS.clear()
    yield
    angela._PREFIX_TOKENS.clear()


def test_prefix_split_subtracts_the_probe_from_both_components():
    client = _Counter(system=500, tools=3000)
    system_tokens, tools_tokens = angela._prefix_tokens(
        client, "m", "SYSTEM", [{"name": "t"}])
    assert (system_tokens, tools_tokens) == (500, 3000)


def test_prefix_split_is_measured_once_per_shape():
    client = _Counter()
    for _ in range(3):
        angela._prefix_tokens(client, "m", "SYSTEM", [{"name": "t"}])
    assert client.calls == 3, "three counts for the first call, none after"


def test_a_different_tool_set_is_measured_again():
    client = _Counter()
    angela._prefix_tokens(client, "m", "SYSTEM", [{"name": "t"}])
    before = client.calls
    angela._prefix_tokens(client, "m", "SYSTEM", [{"name": "t"}, {"name": "u"}])
    assert client.calls > before


def test_no_tools_skips_the_third_count():
    client = _Counter()
    system_tokens, tools_tokens = angela._prefix_tokens(client, "m", "SYSTEM", [])
    assert (system_tokens, tools_tokens) == (500, 0)
    assert client.calls == 2


def test_usage_report_attributes_the_remainder_to_the_conversation():
    resp = _Resp(_Usage(input_tokens=10000, output_tokens=200))
    report = angela._usage_report(resp, system_tokens=500, tools_tokens=3000)
    assert report["system"] == 500
    assert report["tools"] == 3000
    assert report["messages"] == 6500
    assert report["context_window"] == angela.CONTEXT_WINDOW


def test_usage_report_counts_cached_input_as_context():
    """A cache hit still occupies the window; only the price changes."""
    resp = _Resp(_Usage(input_tokens=100, cache_read_input_tokens=9900))
    report = angela._usage_report(resp, system_tokens=500, tools_tokens=3000)
    assert report["messages"] == 6500


def test_usage_report_is_none_when_the_response_carries_no_usage():
    assert angela._usage_report(_Resp(None), 500, 3000) is None


def test_usage_report_is_none_rather_than_zero_when_nothing_was_counted():
    resp = _Resp(_Usage(input_tokens=0))
    assert angela._usage_report(resp, 500, 3000) is None


def test_usage_report_never_reports_a_negative_conversation():
    resp = _Resp(_Usage(input_tokens=100))
    report = angela._usage_report(resp, system_tokens=500, tools_tokens=3000)
    assert report["messages"] == 0
