"""Stream protocol v2: text arrives as deltas, and failures and degraded
modes are expressible as their own events instead of masquerading as answers.

Regression cover for three verified defects in v1:
  - hitting the message cap emitted a `done` with no `text`, so the frontend
    rendered an empty bubble and the explanation was never shown;
  - a failure after a tool call emitted a second `text` event, so the
    abandoned partial answer and the fallback answer were glued together;
  - every `text` event re-sent the whole accumulated string (O(n^2) bytes).
"""
import json

import angela
import config
import pytest


def _no_provider(monkeypatch):
    """Express "no LLM configured" — the whole credential set, not one var.

    Clearing ANTHROPIC_API_KEY alone used to be enough. It isn't: with a
    gateway credential in backend/.env, a provider stays configured and these
    tests silently exercise the REAL model (network, tokens, nondeterminism)
    instead of the degraded path they exist to cover. config.credential_vars()
    is the single source of truth, so a renamed provider can't drift again.
    """
    for var in config.credential_vars():
        monkeypatch.delenv(var, raising=False)


def _events(monkeypatch, **kwargs):
    return list(angela.stream_response("¿cuánta plata tengo parada?", **kwargs))


def test_text_events_carry_deltas_not_accumulated_text(monkeypatch):
    """Concatenating every delta must reproduce the answer exactly once.

    The weak version of this check (`joined.count(deltas[0]) == 1 or
    len(deltas) == 1`) passes trivially whenever the first delta happens to
    be a short/common substring — it doesn't actually prove deltas are
    disjoint fragments. The property that matters is stronger: no delta may
    equal (or be a prefix/suffix repeat of) the running concatenation of the
    deltas before it — i.e. the stream never re-sends a growing snapshot of
    the accumulated text, which is exactly the v1 O(n^2) accumulation bug.
    """
    _no_provider(monkeypatch)
    events = _events(monkeypatch)
    deltas = [e["delta"] for e in events if e["type"] == "text"]
    assert deltas, "expected at least one text event"
    for e in events:
        if e["type"] == "text":
            assert "text" not in e, "v2 text events carry `delta`, not `text`"
    joined = "".join(deltas)
    # A delta stream must not repeat its own prefix (the v1 accumulation bug):
    # no delta after the first may itself contain the accumulation-so-far,
    # which is what an accumulated (rather than incremental) stream would do.
    accumulated_so_far = deltas[0]
    for delta in deltas[1:]:
        assert accumulated_so_far not in delta, (
            "a later delta re-sent the prior accumulated text: "
            "deltas must be disjoint fragments, not growing snapshots"
        )
        accumulated_so_far += delta
    assert accumulated_so_far == joined


def test_no_api_key_emits_a_notice_not_a_silent_answer(monkeypatch):
    _no_provider(monkeypatch)
    events = _events(monkeypatch)
    kinds = [e["kind"] for e in events if e["type"] == "notice"]
    assert "fake_model" in kinds, (
        "a reply produced without the model must say so explicitly"
    )


def test_done_result_has_english_keys_and_no_answer(monkeypatch):
    _no_provider(monkeypatch)
    done = [e for e in _events(monkeypatch) if e["type"] == "done"]
    assert len(done) == 1
    result = done[0]["result"]
    assert set(result) >= {"mode", "tools_used", "actions"}
    assert "answer" not in result, "the text already arrived as deltas"
    assert "respuesta" not in result


def test_model_failure_emits_an_error_event(monkeypatch):
    """A raised model call must surface as `error`, not as a fake answer."""
    _no_provider(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")

    class _Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("model exploded")

    monkeypatch.setattr(angela, "_build_client", _Boom, raising=False)
    events = _events(monkeypatch)
    errors = [e for e in events if e["type"] == "error"]
    assert errors, "a model failure must emit an error event"
    assert errors[0]["code"]
    assert "model exploded" not in json.dumps(events), (
        "raw exception text must not reach the client"
    )


def test_every_event_is_json_serialisable(monkeypatch):
    _no_provider(monkeypatch)
    for e in _events(monkeypatch):
        json.dumps(e, ensure_ascii=False, default=str)
