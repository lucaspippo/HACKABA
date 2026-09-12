"""What a person DID in the interface, for Ángela's next turn.

The deterministic core already shows her every data change: every figure is
recalculated, so a payment recorded by hand is visible the moment she is
asked. What she cannot see is a **decision** — a finding dismissed, a rule
taught, a widget removed. Those are judgments, and nothing in `core/`
recomputes them.

An endpoint that carries a decision records one here. `_prepare_turn` drains
it into the next turn as a labelled block before the user's words, and clears
it. Two rules the callers depend on:

- An event is an **i18n key plus params**, never a sentence. It is rendered at
  drain time in the language of the conversation reading it, which is not
  necessarily the one it was recorded in: the same dismissal must read in
  English to a user working in English.
- Params MUST come from what the endpoint actually did, never from the request
  body. A client that could assert its own events could claim an approval that
  never happened.

MOCK: the queue is a process-level dict, so it dies on restart and does not
cross instances. That matches today's deployment (one web service, no worker —
see render.yaml) and is the seam for real server-side sessions: keep `record`
and `drain`, move `_queues` into the session record.
"""
from __future__ import annotations

import threading

# The block's heading in the prompt. SYSTEM_PROMPT carries this literal, and
# a test asserts the two agree.
LABEL = "ACTIVIDAD EN LA APP DESDE TU ÚLTIMA RESPUESTA"

MAX_EVENTS = 8
MAX_CHARS = 160

_lock = threading.Lock()
_queues: dict[str, list[tuple[str, dict]]] = {}


def clean(text: str) -> str:
    """One printable line, capped. Params come from data (a client's name, an
    imported title) and the note reaches the model unfenced, so the rendered
    line MUST be cleaned. Brackets go too: an event MUST NOT be able to close
    the block it sits inside."""
    raw = str(text or "").replace("[", "(").replace("]", ")")
    printable = "".join(c if c.isprintable() else " " for c in raw)
    return " ".join(printable.split())[:MAX_CHARS].strip()


def record(actor: str | None, event: str, /, **params) -> None:
    """Queue one event for `actor`: an i18n key and its params.

    `actor` and `event` are positional-only so that no template field can
    collide with them — `key` is one a preference event needs.
    """
    if not actor or not event:
        return
    with _lock:
        queue = _queues.setdefault(actor, [])
        queue.append((event, params))
        del queue[:-MAX_EVENTS]  # a burst of clicks MUST NOT grow the prompt


def drain(actor: str | None, lang: str | None = None) -> list[str]:
    """This actor's queued events, rendered in `lang` and removed.

    Read once: a turn that fails after draining loses them. That is the right
    trade — a note that survived would tell Ángela the same thing happened
    twice, and she reports what she is told.
    """
    if not actor:
        return []
    with _lock:
        queued = _queues.pop(actor, [])
    if not queued:
        return []
    import i18n
    rendered = (clean(i18n.t(event, lang, **params)) for event, params in queued)
    return [line for line in rendered if line]


def pending(actor: str | None) -> int:
    """How many events are queued, without draining. For tests and debugging."""
    with _lock:
        return len(_queues.get(actor or "", ()))


def clear() -> None:
    """Drop every queue. Tests, and the seam's obvious no-op on restart."""
    with _lock:
        _queues.clear()
