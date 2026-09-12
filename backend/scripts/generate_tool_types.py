"""Generate TypeScript argument types from angela.py's TOOLS list.

Python is the single source of truth for tool schemas: the tool-use loop and
the per-user feature gating (`tools_para`) both live here. The frontend only
renders tool calls, so it needs the argument shapes as types — generated, not
hand-maintained, so a schema change surfaces at `npm run typecheck`.

TOOLS is read with `ast.literal_eval` instead of by importing angela, which
would pull in `core` and the database.

Run from the repo root or anywhere:  py backend/scripts/generate_tool_types.py
"""
from __future__ import annotations

import ast
import pathlib
import sys

HEADER = """// GENERATED FILE - DO NOT EDIT.
// Source: backend/angela.py (TOOLS)
// Regenerate: py backend/scripts/generate_tool_types.py
//
// Python owns the tool schemas; these types exist so tool-call renderers get
// typed `args` and a schema change fails `npm run typecheck` instead of at
// runtime.
"""

# JSON Schema -> TypeScript. Nested object/array item schemas are not modelled:
# only three tools use them, and a renderer that needs the detail should narrow
# it locally rather than inflate the generator.
TYPE_MAP = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "array": "unknown[]",
    "object": "Record<string, unknown>",
}


def load_tools(angela_path: pathlib.Path) -> list[dict]:
    """Extract the TOOLS literal from angela.py without importing it."""
    tree = ast.parse(angela_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            getattr(target, "id", None) == "TOOLS" for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"No TOOLS assignment found in {angela_path}")


def ts_type(prop: dict) -> str:
    """Map one JSON Schema property to a TypeScript type."""
    return TYPE_MAP.get(prop.get("type"), "unknown")


def render_tool(tool: dict) -> str:
    """Render one tool's argument object type as indented TS members."""
    schema = tool.get("input_schema") or {}
    properties: dict = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    if not properties:
        return f"  {tool['name']}: Record<string, never>;\n"

    lines = [f"  {tool['name']}: {{\n"]
    for name in sorted(properties):
        optional = "" if name in required else "?"
        lines.append(f"    {name}{optional}: {ts_type(properties[name])};\n")
    lines.append("  };\n")
    return "".join(lines)


def render(tools: list[dict]) -> str:
    """Render the whole generated module."""
    out = [HEADER, "\nexport interface ToolArgs {\n"]
    for tool in sorted(tools, key=lambda t: t["name"]):
        out.append(render_tool(tool))
    out.append("}\n\nexport type ToolName = keyof ToolArgs;\n")
    return "".join(out)


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parents[2]
    tools = load_tools(repo / "backend" / "angela.py")
    target = repo / "frontend" / "src" / "lib" / "chat" / "toolArgs.generated.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(tools), encoding="utf-8")
    print(f"Wrote {len(tools)} tool types to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
