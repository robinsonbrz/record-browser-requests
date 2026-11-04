"""Inferência simplificada de schema (estilo JSON Schema) a partir de amostras."""

from typing import Any

Schema = dict[str, Any]


def infer(value: Any) -> Schema:
    if isinstance(value, dict):
        return {
            "type": "object",
            "properties": {k: infer(v) for k, v in value.items()},
            "required": sorted(value.keys()),
        }
    if isinstance(value, list):
        items: Schema | None = None
        for v in value:
            items = merge(items, infer(v))
        return {"type": "array", "items": items or {}}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if value is None:
        return {"type": "null"}
    return {"type": "string"}


def _types(s: Schema) -> list[str]:
    t = s.get("type")
    if isinstance(t, list):
        return t
    return [t] if isinstance(t, str) else []


def _variants(s: Schema) -> list[Schema]:
    return s.get("anyOf", [s])


def merge(a: Schema | None, b: Schema | None) -> Schema | None:
    if a is None:
        return b
    if b is None or a == b:
        return a
    ta, tb = a.get("type"), b.get("type")
    if ta == tb == "object":
        props = dict(a.get("properties", {}))
        for k, v in b.get("properties", {}).items():
            props[k] = merge(props.get(k), v)
        required = sorted(set(a.get("required", [])) & set(b.get("required", [])))
        return {"type": "object", "properties": props, "required": required}
    if ta == tb == "array":
        return {
            "type": "array",
            "items": merge(a.get("items") or None, b.get("items") or None) or {},
        }

    variants: list[Schema] = []
    for s in _variants(a) + _variants(b):
        if s not in variants:
            variants.append(s)
    primitives = all(
        set(_types(s)) & {"string", "integer", "number", "boolean", "null"}
        and "properties" not in s
        and "items" not in s
        for s in variants
    )
    if primitives:
        types = sorted({t for s in variants for t in _types(s)})
        return {"type": types[0] if len(types) == 1 else types}
    return {"anyOf": variants}


def infer_many(samples: list[Any]) -> Schema | None:
    result: Schema | None = None
    for s in samples:
        result = merge(result, infer(s))
    return result
