"""Build and send one request (with httpx + asyncio), and turn it into a curl command."""
import json
import shlex
import time

import httpx


def build_request(target):
    """Turn a target into (method, full url, headers, json body).

    Both send() and to_curl() use this, so the curl command in the report
    is exactly the request that was sent.
    """
    url = target["url"]
    for name, value in target.get("path", {}).items():
        url = url.replace("{" + name + "}", str(value))
    url = str(httpx.URL(url, params=target.get("query") or None))
    return target.get("method", "GET"), url, target.get("headers", {}), target.get("body")


async def send(target, timeout=10):
    """Send one request. Returns (status, response text, seconds taken).

    status is None if the server did not answer, and "skipped" if the
    request could not even be sent (for example, an emoji in a header).
    """
    method, url, headers, body = build_request(target)
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, headers=headers, json=body)
            return response.status_code, response.text, time.perf_counter() - start
    except httpx.HTTPError as error:
        return None, str(error) or type(error).__name__, time.perf_counter() - start
    except Exception as error:
        return "skipped", f"could not send this request: {error}", time.perf_counter() - start


def to_curl(target):
    """Make a curl command that repeats this request, so a problem is easy to reproduce."""
    method, url, headers, body = build_request(target)
    parts = ["curl", "-X", method, url]
    for name, value in headers.items():
        parts += ["-H", f"{name}: {value}"]
    if body is not None:
        parts += ["-H", "Content-Type: application/json", "-d", json.dumps(body, ensure_ascii=False)]
    return " ".join(shlex.quote(part) for part in parts)

