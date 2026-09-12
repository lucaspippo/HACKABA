"""Stream protocol v2: text arrives as deltas, and failures are expressible
as their own events instead of masquerading as answers.

Regression cover for three verified defects in v1:
  - hitting the message cap emitted a `done` with no `text`, so the frontend
    rendered an empty bubble and the explanation was never shown;
  - a failure after a tool call emitted a second `text` event, so the
    abandoned partial answer and a canned fallback were glued together;
  - every `text` event re-sent the whole accumulated string (O(n^2) bytes).
"""
import json

import angela
import config


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


def test_no_api_key_emits_error_not_a_fake_answer(monkeypatch):
    """A missing model is a config error. It must not invent a reply."""
    _no_provider(monkeypatch)
    events = _events(monkeypatch)
    assert not any(e["type"] == "text" for e in events), (
        "without a model the stream must not emit a canned answer"
    )
    assert not any(e["type"] == "notice" for e in events), (
        "fake_model notices are gone; this is an error, not a labelled fake"
    )
    errors = [e for e in events if e["type"] == "error"]
    assert errors and errors[0]["code"] == "model_unavailable"
    assert errors[0].get("retryable") is False


def test_done_result_has_english_keys_and_no_answer(monkeypatch):
    _no_provider(monkeypatch)
    done = [e for e in _events(monkeypatch) if e["type"] == "done"]
    assert len(done) == 1
    result = done[0]["result"]
    assert set(result) >= {"mode", "tools_used", "actions"}
    assert "answer" not in result, "the text already arrived as deltas"
    assert "respuesta" not in result
    assert result["mode"] == "error"


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


def test_responder_without_model_is_an_error(monkeypatch):
    _no_provider(monkeypatch)
    r = angela.responder("¿quién me debe plata?")
    assert r["mode"] == "error"
    assert r["error"] == "model_unavailable"
    assert r["answer"] == ""
    assert r["tools_used"] == []


def test_every_event_is_json_serialisable(monkeypatch):
    _no_provider(monkeypatch)
    for e in _events(monkeypatch):
        json.dumps(e, ensure_ascii=False, default=str)
