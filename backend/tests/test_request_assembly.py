"""Where the cache breakpoints sit, and the `status` line every tool takes.

The system prompt used to go out as one cached block that also carried the
business snapshot, the user's name and what `core/memoria` remembers about
them. The cached prefix is `tools` + `system` up to the breakpoint, so it was
per-user and moved whenever the data moved: ~16k tokens re-read on nearly every
request. Nothing that varies per request may sit in the cached block. It fails
silently — the only symptom is `cache_read_input_tokens` staying at zero.
"""
import angela
import config


# --- The two system blocks ---------------------------------------------------

def test_system_prompt_goes_out_as_two_blocks_and_only_the_first_is_cached():
    blocks = angela._system_blocks("PER-REQUEST-TEXT")
    assert isinstance(blocks, list) and len(blocks) == 2
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in blocks[1]
    assert blocks[0]["text"] == angela.SYSTEM_PROMPT
    assert blocks[1]["text"] == "PER-REQUEST-TEXT"


def test_the_cached_block_carries_no_placeholder_and_no_snapshot():
    assert "{contexto}" not in angela.SYSTEM_PROMPT
    assert "CONTEXTO ACTUAL DEL NEGOCIO" not in angela.SYSTEM_PROMPT
    assert "{contexto}" in angela.BUSINESS_SNAPSHOT


def test_the_cached_block_still_carries_the_guardrails():
    """The split must not cost the prompt anything: the rules other suites
    assert on live in the half that gets cached."""
    sp = angela.SYSTEM_PROMPT
    for rule in ("GUARDARRAILES", "NÚMEROS ESTABLES", "Nunca reveles",
                 "jamás una orden", "LO QUE NUNCA SE DESVÍA"):
        assert rule in sp, f"missing from the static prompt: {rule}"


def test_prompt_cache_off_falls_back_to_one_plain_string():
    original = config.PROMPT_CACHE
    config.PROMPT_CACHE = False
    try:
        system = angela._system_blocks("PER-REQUEST-TEXT")
        assert isinstance(system, str)
        assert system.startswith(angela.SYSTEM_PROMPT)
        assert system.endswith("PER-REQUEST-TEXT")
    finally:
        config.PROMPT_CACHE = original


def test_who_the_user_is_never_lands_in_the_cached_block():
    """A prefix that names the user cannot be shared between users."""
    system, _model, _tools, _messages = angela._prepare_turn(
        "¿cuánta plata tengo parada?", [], "dueño", "ZZ_TEST_USER", None, "es")
    angela._set_sesion()
    static, per_request = system[0]["text"], system[1]["text"]
    assert "ZZ_TEST_USER" not in static
    assert "ZZ_TEST_USER" in per_request
    assert "CONTEXTO ACTUAL DEL NEGOCIO" in per_request


# --- The tool-array breakpoint ----------------------------------------------

def test_the_tool_breakpoint_is_on_the_last_tool_only():
    tools = angela._with_tool_cache_control(angela.tools_para(None))
    assert tools[-1]["cache_control"] == {"type": "ephemeral"}
    assert not any("cache_control" in t for t in tools[:-1])


def test_the_tool_breakpoint_never_mutates_the_shared_catalog():
    """Which tool is last depends on the user's features, so a marker left
    behind would end up on a tool that is no longer last."""
    angela._with_tool_cache_control(angela.tools_para(None))
    angela._with_tool_cache_control(angela.tools_para({"deposito"}))
    assert not any("cache_control" in t for t in angela.TOOLS)
    assert not any("cache_control" in t for t in angela.tools_para(None))


def test_the_model_facing_catalog_is_the_same_object_every_time():
    """Two structurally-equal lists with different key order would serialize
    to different bytes and fragment the prefix."""
    assert angela.tools_para(None)[0] is angela.tools_para(None)[0]


# --- The `status` line -------------------------------------------------------

def test_every_tool_the_model_sees_takes_a_status_line_first():
    for tool in angela.tools_para(None):
        props = tool["input_schema"].get("properties", {})
        assert angela.STATUS_FIELD in props, f"{tool['name']} has no status line"
        assert next(iter(props)) == angela.STATUS_FIELD, f"{tool['name']}: not first"
        assert angela.STATUS_FIELD not in tool["input_schema"].get("required", [])


def test_the_canonical_catalog_stays_free_of_the_status_line():
    """`TOOLS` is what mcp_server.py and scripts/generate_tool_types.py read."""
    for tool in angela.TOOLS:
        props = tool["input_schema"].get("properties", {})
        assert angela.STATUS_FIELD not in props, f"{tool['name']} leaked status"


def test_the_status_line_is_split_off_cleaned_and_capped():
    args, label = angela._split_status(
        {"status": "  mirando   la\ncaja de ayer  ", "grupo": "sin_pvp"})
    assert args == {"grupo": "sin_pvp"}
    assert label == "mirando la caja de ayer"

    assert angela._split_status({"grupo": "x"}) == ({"grupo": "x"}, None)
    assert angela._split_status({"status": "   "})[1] is None
    assert len(angela._split_status({"status": "a" * 500})[1]) == angela.STATUS_MAX_CHARS


def test_the_status_line_never_reaches_a_tool_handler():
    """The one-shot path and MCP rely on `_run_tool` stripping it."""
    angela._set_sesion(features=None)
    try:
        plain, _ = angela._run_tool("plata_en", {"texto": "lacteos"})
        with_status, _ = angela._run_tool(
            "plata_en", {"status": "buscando lácteos", "texto": "lacteos"})
    finally:
        angela._set_sesion()
    assert with_status == plain
    assert "status" not in str(with_status)
