"""Read the bad inputs from the payloads/ folder."""
import json
import os

PAYLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "payloads")


def load_payloads():
    """Read every .txt file in the payloads folder.

    Returns a dict like {"xss": ["<script>...", ...], "sql_injection": [...]}.
    Each line in a file is one payload.
    """
    payloads = {}
    for filename in sorted(os.listdir(PAYLOAD_FOLDER)):
        if not filename.endswith(".txt"):
            continue
        category = filename[:-4]
        with open(os.path.join(PAYLOAD_FOLDER, filename), encoding="utf-8") as f:
            lines = f.read().splitlines()
        payloads[category] = [parse_line(line) for line in lines if line != ""]
    return payloads


def parse_line(line):
    """Turn one line of a payload file into the value we send.

    If the line is valid JSON (like 123, null, true, [] or "") we send that
    JSON value, so we can test wrong types. Otherwise we send the text as-is.
    """
    try:
        return json.loads(line)
    except ValueError:
        return line

