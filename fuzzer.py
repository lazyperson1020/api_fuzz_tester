"""
A simple API fuzzer. This file is the command line; the work is done in apifuzzer/.

It takes an API you describe in a JSON file (see the targets/ folder) or an
OpenAPI spec, replaces each input field with every payload from the payloads/
folder, sends the requests, and reports anything that looks like a bug.

Usage:
    python fuzzer.py targets/create_user.json
    python fuzzer.py openapi.yaml --base-url http://localhost:5000
    python fuzzer.py --help        (shows all options)
"""
import asyncio
import json
import sys

import click

from apifuzzer.auth import auth_headers
from apifuzzer.openapi import is_openapi, load_spec, targets_from_spec
from apifuzzer.payloads import load_payloads
from apifuzzer.runner import fuzz_all, short


def load_targets(source, base_url):
    """Read one input: either a single target file or an OpenAPI spec (many targets)."""
    data = load_spec(source)
    if not is_openapi(data):
        if not isinstance(data, dict) or "url" not in data:
            raise ValueError("this is not a target file (no \"url\") and not an OpenAPI spec")
        return [data]

    if not base_url:
        servers = data.get("servers", [])
        if not servers or not servers[0].get("url", "").startswith("http"):
            raise ValueError("the spec does not say where the API runs, please add --base-url http://...")
        base_url = servers[0]["url"]
    targets = targets_from_spec(data, base_url.rstrip("/"))
    print(f"Found {len(targets)} endpoints in {source}")
    return targets


EXAMPLES = """\b
Examples:
  python fuzzer.py targets/create_user.json
  python fuzzer.py targets/*.json --quiet
  python fuzzer.py openapi.yaml --base-url http://localhost:5000
  python fuzzer.py targets/login.json --auth bearer:abc123 -p xss,sql_injection
"""



@click.command(epilog=EXAMPLES)
@click.argument("inputs", nargs=-1)
@click.option("-u", "--base-url", help="Base URL of the API (for OpenAPI specs). Default: the spec's 'servers' entry.")
@click.option("-a", "--auth", default="none", show_default=True,
              help="Authentication: none, bearer:TOKEN, basic:USER:PASS or apikey:HEADER:KEY.")
@click.option("-H", "--header", "extra_headers", multiple=True,
              help='Extra header for every request, e.g. "X-Tenant: 42". Can be repeated.')
@click.option("-p", "--payloads", "payload_names", help="Only use these payload files, comma separated, e.g. xss,sql_injection.")
@click.option("--list-payloads", is_flag=True, help="Show the available payload files and exit.")
@click.option("-o", "--output", default="report.json", show_default=True, help="Where to save the report.")
@click.option("-c", "--concurrency", default=5, show_default=True, help="How many requests to send at the same time.")
@click.option("-t", "--timeout", default=10.0, show_default=True, help="Seconds to wait for each response.")
@click.option("--slow", default=3.0, show_default=True, help="Report responses slower than this many seconds.")
@click.option("--delay", default=0.0, show_default=True, help="Seconds to wait after each request, to go easy on the server.")
@click.option("-q", "--quiet", is_flag=True, help="Only print requests that found a problem.")
def main(inputs, base_url, auth, extra_headers, payload_names, list_payloads,
         output, concurrency, timeout, slow, delay, quiet):
    """Send bad input to an API and report anything that breaks.

    INPUTS are target .json files, or an OpenAPI spec (file or URL).
    """
    payloads = load_payloads()
    if list_payloads:
        for category, values in payloads.items():
            print(f"{category:<20} {len(values)} payloads")
        return
    if payload_names:
        wanted = [name.strip() for name in payload_names.split(",")]
        unknown = [name for name in wanted if name not in payloads]
        if unknown:
            raise click.UsageError(f"unknown payload file(s): {', '.join(unknown)} (see --list-payloads)")
        payloads = {name: payloads[name] for name in wanted}

    if not inputs:
        raise click.UsageError("please give at least one target file or OpenAPI spec")

    try:
        headers = auth_headers(auth)
    except ValueError as error:
        raise click.UsageError(str(error))
    for header in extra_headers:
        name, _, value = header.partition(":")
        headers[name.strip()] = value.strip()

    targets = []
    for source in inputs:
        try:
            targets += load_targets(source, base_url)
        except Exception as error:
            raise click.ClickException(f"Could not read {source}: {error}")
    for target in targets:
        target["headers"] = {**target.get("headers", {}), **headers}

    print(f"Loaded {sum(len(v) for v in payloads.values())} payloads from {len(payloads)} files")

    total, report = asyncio.run(fuzz_all(targets, payloads, timeout, concurrency, delay, slow, quiet))

    print(f"\n=== Done: sent {total} requests, found {len(report)} problems ===")
    for item in report:
        print(f"- {item['endpoint']}  {item['field']}: {item['problem']}  (payload {short(item['payload'])})")

    with open(output, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nFull report (with a curl command for each problem) saved to {output}")

    sys.exit(1 if report else 0)


if __name__ == "__main__":
    main()
