"""Generate the TypeScript contract for GET /calendar/month from FastAPI."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "app"))

from main import app

OUTPUT = ROOT / "shared" / "calendar-month.generated.ts"


def render_calendar_contract(openapi: dict) -> str:
    schemas = openapi["components"]["schemas"]
    endpoint = openapi["paths"]["/calendar/month"]["get"]
    response = endpoint["responses"]["200"]["content"]["application/json"]["schema"]
    names: dict[str, None] = {}

    def ts_type(schema: dict) -> str:
        if "$ref" in schema:
            prefix = "#/components/schemas/"
            reference = schema["$ref"]
            if not reference.startswith(prefix):
                raise ValueError(f"Unsupported reference: {reference}")
            name = reference.removeprefix(prefix)
            names[name] = None
            return name
        if "anyOf" in schema:
            return " | ".join(ts_type(variant) for variant in schema["anyOf"])
        if "enum" in schema:
            return " | ".join(json.dumps(value) for value in schema["enum"])
        if schema.get("type") == "array":
            return f"Array<{ts_type(schema['items'])}>"
        primitives = {
            "string": "string", "integer": "number", "number": "number",
            "boolean": "boolean", "null": "null",
        }
        if schema.get("type") in primitives:
            return primitives[schema["type"]]
        raise ValueError(f"Unsupported calendar field: {schema}")

    ts_type(response)
    blocks: list[str] = []
    emitted: set[str] = set()
    while remaining := [name for name in names if name not in emitted]:
        for name in remaining:
            schema = schemas[name]
            required = set(schema.get("required", []))
            fields = [
                f"  {field}{'' if field in required else '?'}: {ts_type(value)};"
                for field, value in schema["properties"].items()
            ]
            blocks.append("\n".join([f"export type {name} = {{", *fields, "};"]))
            emitted.add(name)
    return "\n\n".join(blocks) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render_calendar_contract(app.openapi())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            raise SystemExit("Run python scripts/generate-calendar-contract.py to update the contract.")
    else:
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8")
