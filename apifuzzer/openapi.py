"""
Turn an OpenAPI spec into targets for the fuzzer.

A "target" is the same thing you would write by hand in the targets/ folder:
    {"method": "POST", "url": "...", "path": {...}, "query": {...}, "body": {...}}

This file reads a spec, and for every endpoint builds a target filled with
normal example values. The fuzzer then replaces those values with payloads.
"""
import httpx
import yaml


def load_spec(source):
    """Read a spec from a URL or a file. Works with JSON and YAML."""
    if source.startswith("http://") or source.startswith("https://"):
        text = httpx.get(source, timeout=10).text
    else:
        with open(source, encoding="utf-8") as f:
            text = f.read()
    return yaml.safe_load(text)


def is_openapi(data):
    """True if the loaded data looks like an OpenAPI/Swagger spec."""
    return isinstance(data, dict) and ("openapi" in data or "swagger" in data)


def resolve(spec, schema):
    """Follow a {"$ref": "#/components/schemas/User"} link to the real schema."""
    while isinstance(schema, dict) and "$ref" in schema:
        found = spec
        for part in schema["$ref"].lstrip("#/").split("/"):
            found = found[part]
        schema = found
    return schema or {}


def example_value(spec, schema, depth=0):
    """Make a normal, valid-looking value for a schema."""
    schema = resolve(spec, schema)
    if depth > 5:
        return None
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema:
        return schema["enum"][0]

    kind = schema.get("type", "object" if "properties" in schema else "string")
    if kind == "integer":
        return schema.get("minimum", 1)
    if kind == "number":
        return schema.get("minimum", 1.5)
    if kind == "boolean":
        return True
    if kind == "array":
        return [example_value(spec, schema.get("items", {}), depth + 1)]
    if kind == "object":
        properties = schema.get("properties", {})
        return {name: example_value(spec, s, depth + 1) for name, s in properties.items()}

    formats = {
        "email": "test@example.com",
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "date": "2024-01-01",
        "date-time": "2024-01-01T00:00:00Z",
        "uri": "https://example.com",
    }
    return formats.get(schema.get("format"), "test")


def targets_from_spec(spec, base_url):
    """Build one target per endpoint (path + method) in the spec."""
    targets = []
    for path, methods in spec.get("paths", {}).items():
        for method in ["get", "post", "put", "patch", "delete"]:
            if method not in methods:
                continue
            operation = methods[method]
            target = {"method": method.upper(), "url": base_url + path,
                      "headers": {}, "path": {}, "query": {}}

            for param in methods.get("parameters", []) + operation.get("parameters", []):
                param = resolve(spec, param)
                value = example_value(spec, param.get("schema", param))
                if param["in"] == "path":
                    target["path"][param["name"]] = value
                elif param["in"] == "query":
                    target["query"][param["name"]] = value
                elif param["in"] == "header":
                    target["headers"][param["name"]] = str(value)

            body = resolve(spec, operation.get("requestBody", {}))
            json_body = body.get("content", {}).get("application/json")
            if json_body:
                value = example_value(spec, json_body.get("schema", {}))
                if isinstance(value, dict):
                    target["body"] = value

            targets.append(target)
    return targets
