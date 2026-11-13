"""Decide if a response looks like a bug."""

ERROR_WORDS = ["Traceback", "Exception", "SQL syntax", "sqlite3", "psycopg2", "ORA-0", "at java."]


def find_problems(category, payload, status, text, seconds, slow_seconds=3):
    """Look at one response and return a list of problems (empty if it looks fine)."""
    if status == "skipped":
        return []

    problems = []

    if status is None:
        problems.append("no response (server crashed, closed the connection or timed out)")
    elif status >= 500:
        problems.append(f"server error {status}")

    for word in ERROR_WORDS:
        if word in text:
            problems.append(f"error details leaked in response ('{word}')")
            break

    if category == "xss" and status is not None and status < 300 and str(payload) in text:
        problems.append("XSS payload returned unescaped")

    if seconds > slow_seconds:
        problems.append(f"slow response ({seconds:.1f}s)")

    return problems

