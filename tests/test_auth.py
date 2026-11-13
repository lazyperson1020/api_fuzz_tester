from apifuzzer.auth import auth_headers


def test_auth_option_becomes_headers():
    assert auth_headers("none") == {}
    assert auth_headers("bearer:abc") == {"Authorization": "Bearer abc"}
    assert auth_headers("basic:user:pass") == {"Authorization": "Basic dXNlcjpwYXNz"}
    assert auth_headers("apikey:X-API-Key:secret") == {"X-API-Key": "secret"}

