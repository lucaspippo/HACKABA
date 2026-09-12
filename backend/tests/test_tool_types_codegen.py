"""The generated TS tool types must stay in sync with angela.py's TOOLS.

Python owns the tool schemas (the loop and the feature gating are Python);
the TS types are generated. This test fails loudly when someone edits a
tool schema and forgets to regenerate.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "scripts"))

import generate_tool_types as gen  # noqa: E402

GENERATED = REPO / "frontend" / "src" / "lib" / "chat" / "toolArgs.generated.ts"


def test_tools_parse_without_importing_angela():
    tools = gen.load_tools(REPO / "backend" / "angela.py")
    assert len(tools) > 40
    assert all("name" in t and "input_schema" in t for t in tools)
    assert "consultar_serie" in {t["name"] for t in tools}


def test_json_schema_type_mapping():
    assert gen.ts_type({"type": "string"}) == "string"
    assert gen.ts_type({"type": "integer"}) == "number"
    assert gen.ts_type({"type": "number"}) == "number"
    assert gen.ts_type({"type": "boolean"}) == "boolean"
    assert gen.ts_type({"type": "array"}) == "unknown[]"
    assert gen.ts_type({"type": "object"}) == "Record<string, unknown>"
    assert gen.ts_type({}) == "unknown"


def test_required_properties_are_not_optional():
    rendered = gen.render_tool({
        "name": "demo_tool",
        "input_schema": {
            "type": "object",
            "properties": {"source": {"type": "string"}, "top_n": {"type": "integer"}},
            "required": ["source"],
        },
    })
    assert "source: string;" in rendered
    assert "top_n?: number;" in rendered


def test_generated_file_is_current():
    expected = gen.render(gen.load_tools(REPO / "backend" / "angela.py"))
    actual = GENERATED.read_text(encoding="utf-8")
    assert actual == expected, (
        "frontend/src/lib/chat/toolArgs.generated.ts is stale. "
        "Regenerate with: py backend/scripts/generate_tool_types.py"
    )
