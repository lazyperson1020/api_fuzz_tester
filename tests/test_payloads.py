from apifuzzer.payloads import load_payloads, parse_line


def test_payload_lines_are_read_as_json_or_text():
    assert parse_line("null") is None
    assert parse_line("-1") == -1
    assert parse_line("' OR 1=1 --") == "' OR 1=1 --"


def test_all_payload_files_are_loaded():
    payloads = load_payloads()
    assert "xss" in payloads
    assert "<script>alert(1)</script>" in payloads["xss"]

