"""Run the fuzzing: build the tests for each endpoint, send them, and collect the problems."""
import asyncio
import copy
import json

from .checks import find_problems
from .sender import send, to_curl


def short(value, length=40):
    """Shorten a value so it fits on one line when printed."""
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= length else text[:length] + "..."


async def fuzz_target(target, payloads, timeout, concurrency, delay, slow, quiet):
    """Fuzz one endpoint. Returns (number of requests sent, list of problems)."""
    endpoint = f"{target.get('method', 'GET')} {target['url']}"
    print(f"\n########## {endpoint} ##########")

    status, text, seconds = await send(target, timeout)
    print(f"Normal request -> {status} ({seconds:.2f}s)")
    if not isinstance(status, int) or status >= 400:
        print("WARNING: the normal request already fails, so results may not mean much.")

    tests = []
    for section in ["path", "query", "body"]:
        for field in target.get(section, {}):
            for category, values in payloads.items():
                for payload in values:
                    test = copy.deepcopy(target)
                    test[section][field] = payload
                    tests.append((f"{section}.{field}", category, payload, test))

    limit = asyncio.Semaphore(concurrency)

    async def send_limited(test):
        async with limit:
            result = await send(test, timeout)
            await asyncio.sleep(delay)
            return result

    results = await asyncio.gather(*(send_limited(test) for _, _, _, test in tests))

    report = []
    last_field = None
    for (field, category, payload, test), (status, text, seconds) in zip(tests, results):
        if field != last_field:
            print(f"\n--- Fuzzing {field} ---")
            last_field = field

        problems = find_problems(category, payload, status, text, seconds, slow)
        line = f"[{status}] {category:<20} {short(payload)}"
        if problems:
            line += "   <-- PROBLEM: " + ", ".join(problems)
        if problems or not quiet:
            print(line)

        for problem in problems:
            report.append({
                "endpoint": endpoint,
                "field": field,
                "category": category,
                "payload": payload,
                "status": status,
                "problem": problem,
                "curl": to_curl(test),
            })

    return len(tests), report


async def fuzz_all(targets, payloads, timeout, concurrency, delay, slow, quiet):
    """Fuzz every target, one endpoint after another."""
    total = 0
    report = []
    for target in targets:
        sent, problems = await fuzz_target(target, payloads, timeout, concurrency, delay, slow, quiet)
        total += sent
        report += problems
    return total, report

