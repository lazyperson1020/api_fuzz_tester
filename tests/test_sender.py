from apifuzzer.sender import to_curl


def test_curl_command_repeats_the_request():
    target = {
        "method": "POST",
        "url": "http://api/users/{id}",
        "path": {"id": 7},
        "query": {"q": "it's"},
        "headers": {"Authorization": "Bearer abc"},
        "body": {"name": "' OR 1=1 --"},
    }
    assert to_curl(target) == (
        "curl -X POST 'http://api/users/7?q=it%27s' -H 'Authorization: Bearer abc' "
        "-H 'Content-Type: application/json' -d '{\"name\": \"'\"'\"' OR 1=1 --\"}'"
    )

