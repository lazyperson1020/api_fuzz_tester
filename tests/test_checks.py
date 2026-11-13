from apifuzzer.checks import find_problems


def test_normal_response_has_no_problems():
    assert find_problems("sql_injection", "' OR 1=1 --", 400, "bad input", 0.1) == []


def test_server_error_is_reported():
    assert "server error 500" in find_problems("wrong_types", -1, 500, "", 0.1)


def test_leaked_error_is_reported():
    problems = find_problems("wrong_types", -1, 500, "Traceback (most recent call last)", 0.1)
    assert any("leaked" in p for p in problems)


def test_reflected_xss_is_reported():
    payload = "<script>alert(1)</script>"
    assert "XSS payload returned unescaped" in find_problems("xss", payload, 200, f"<p>{payload}</p>", 0.1)


def test_slow_and_no_response_are_reported():
    assert find_problems("long_input", "A", 200, "", 5.0) == ["slow response (5.0s)"]
    assert any("no response" in p for p in find_problems("xss", "x", None, "", 0.1))


def test_skipped_request_is_not_a_problem():
    assert find_problems("special_characters", "😀", "skipped", "could not send", 0.0) == []

