from apifuzzer.openapi import is_openapi, targets_from_spec

SPEC = {
    "openapi": "3.0.0",
    "paths": {
        "/users/{user_id}": {
            "get": {
                "parameters": [
                    {"name": "user_id", "in": "path", "schema": {"type": "integer"}},
                    {"name": "verbose", "in": "query", "schema": {"type": "boolean"}},
                ]
            }
        },
        "/users": {
            "post": {
                "requestBody": {
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}
                }
            }
        },
    },
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "age": {"type": "integer"},
                },
            }
        }
    },
}


def test_detects_openapi():
    assert is_openapi(SPEC)
    assert not is_openapi({"method": "GET", "url": "http://x"})


def test_one_target_per_endpoint():
    get_user, create_user = targets_from_spec(SPEC, "http://api")

    assert get_user["method"] == "GET"
    assert get_user["url"] == "http://api/users/{user_id}"
    assert get_user["path"] == {"user_id": 1}
    assert get_user["query"] == {"verbose": True}

    assert create_user["method"] == "POST"
    assert create_user["body"] == {"name": "test", "email": "test@example.com", "age": 1}
