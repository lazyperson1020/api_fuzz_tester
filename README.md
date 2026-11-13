# apifuzzer

A very simple API fuzzer. You describe an API in a small JSON file (or give it
an OpenAPI spec), and the fuzzer sends it lots of bad input (SQL injection, XSS, wrong types, very long
text, ...) to find bugs.


## Project layout

```
fuzzer.py              the command line (run this)
apifuzzer/             the fuzzer itself, one job per file:
    payloads.py          read the bad inputs from payloads/
    openapi.py           turn an OpenAPI spec into targets
    auth.py              turn the --auth option into headers
    sender.py            send one request, and make a curl command for it
    checks.py            decide if a response looks like a bug
    runner.py            fuzz each endpoint: build the tests, send them, collect problems
payloads/              the bad inputs, one .txt file per type, one payload per line
targets/               your API descriptions (one .json file per endpoint)
examples/demo_api.py   a small buggy API to practise on
tests/                 one test file per module in apifuzzer/
```

How a run flows: `fuzzer.py` reads your options → `openapi.py` (or a target
file) gives the endpoints → `payloads.py` gives the bad inputs → `runner.py`
makes one test per field and payload → `sender.py` sends them → `checks.py`
looks for problems → `fuzzer.py` prints the summary and saves the report.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Try it on the demo API

```bash
# terminal 1: start the buggy demo API
python examples/demo_api.py

# terminal 2: fuzz one endpoint from a target file
python fuzzer.py targets/create_user.json

# ...or fuzz every endpoint at once using the API's OpenAPI spec
python fuzzer.py http://127.0.0.1:8000/openapi.json --base-url http://127.0.0.1:8000
```

## Fuzz your own API

Create a file in `targets/`, for example `targets/login.json`:

```json
{
  "method": "POST",
  "url": "http://localhost:5000/login",
  "headers": { "Authorization": "Bearer YOUR_TOKEN" },
  "body": { "username": "alice", "password": "secret123" }
}
```

Then run:

```bash
python fuzzer.py targets/login.json
```

Each part of the target file:

| Key       | What it is | Fuzzed? |
|-----------|------------|---------|
| `method`  | GET, POST, PUT, DELETE, ... | no |
| `url`     | The full URL. Put path values in braces: `/users/{id}` | no |
| `headers` | Headers sent with every request (e.g. auth) | no |
| `path`    | Values for the `{...}` parts of the URL | yes |
| `query`   | Query string values (`?q=books&limit=10`) | yes |
| `body`    | The JSON body | yes |

## Fuzz your own API with an OpenAPI spec

If your API has an OpenAPI (Swagger) spec, you don't need to write target files:

```bash
python fuzzer.py openapi.yaml --base-url http://localhost:5000
python fuzzer.py http://localhost:5000/openapi.json --base-url http://localhost:5000
```

`--base-url` is where the API is running. You can leave it out if the spec
has a `servers` entry with a full URL.

`apifuzzer/openapi.py` reads the spec and, for every endpoint, builds a target just like
the ones in `targets/`. It fills each field with a normal value (the spec's
`example` or `default` if there is one, otherwise a simple value like `"test"`
or `1`). Then the fuzzer runs on every endpoint, one after another.

Header parameters from the spec are sent but not fuzzed. Use `--auth` to log in.
JSON and YAML specs both work.

## How fuzzing works

Use **normal, working values** in the target file. The fuzzer first sends your
request as-is, then changes **one field at a time** to each payload, so when
something breaks you know exactly which field and payload caused it.

Requests are sent with `httpx` using `asyncio`, several at the same time
(5 by default, change it with `--concurrency`). Endpoints are tested one after
another, and results are always printed in the same order.

## What it reports

- **server error 5xx**: the server crashed on the input
- **no response**: the connection was closed or timed out
- **error details leaked**: the response contains a stack trace or database error
- **XSS payload returned unescaped**: the request was accepted and the script was sent back as-is
- **slow response**: the request took longer than 3 seconds

A request shown as `[skipped]` could not be sent at all (for example, an emoji
can't be put in an HTTP header). It is not counted as a problem.

Every request is printed with its status code. Problems are marked with
`<-- PROBLEM`, listed again at the end, and saved to `report.json`.

## The report

Each problem in `report.json` looks like this:

```json
{
  "endpoint": "POST http://127.0.0.1:8000/users",
  "field": "body.age",
  "category": "wrong_types",
  "payload": -1,
  "status": 500,
  "problem": "server error 500",
  "curl": "curl -X POST http://127.0.0.1:8000/users -H 'Content-Type: application/json' -d '{\"name\": \"test\", \"age\": -1, \"bio\": \"\"}'"
}
```

Paste the `curl` command into a terminal to send the exact same request again.
This makes it easy to reproduce and debug the problem.

## Command line options

Run `python fuzzer.py --help` to see them all.

| Option | What it does | Default |
|--------|--------------|---------|
| `-u`, `--base-url URL` | Where the API runs (for OpenAPI specs) | the spec's `servers` |
| `-a`, `--auth VALUE` | Log in: `bearer:TOKEN`, `basic:USER:PASS` or `apikey:HEADER:KEY` | `none` |
| `-H`, `--header "Name: value"` | Add any other header to every request. Can be used many times | none |
| `-p`, `--payloads xss,sql_injection` | Only use these payload files | all |
| `--list-payloads` | Show the payload files and how many payloads each has | |
| `-o`, `--output FILE` | Where to save the report | `report.json` |
| `-c`, `--concurrency N` | How many requests to send at the same time | 5 |
| `-t`, `--timeout SECONDS` | How long to wait for each response | 10 |
| `--slow SECONDS` | Report responses slower than this | 3 |
| `--delay SECONDS` | Wait between requests, to go easy on the server | 0 |
| `-q`, `--quiet` | Only print requests that found a problem | off |

You can also give several target files at once: `python fuzzer.py targets/*.json`.

Examples:

```bash
# fuzz every target file, only show problems
python fuzzer.py targets/*.json -q

# only test XSS and SQL injection, with a login token
python fuzzer.py targets/login.json -p xss,sql_injection --auth bearer:abc123

# other kinds of login
python fuzzer.py openapi.yaml -u http://localhost:5000 --auth basic:alice:secret
python fuzzer.py openapi.yaml -u http://localhost:5000 --auth apikey:X-API-Key:abc123

# a slow or fragile server: one request at a time, wait longer, pause between requests
python fuzzer.py openapi.yaml -u http://localhost:5000 -c 1 --timeout 30 --delay 0.5
```

**Exit code:** `0` means no problems were found, and `1` means problems were found
or an input couldn't be read. Scripts and CI can use this.

## Adding payloads

Open any file in `payloads/` and add a line, or create a new `.txt` file.
The file name becomes the category name.

- Each line is one payload.
- If a line is valid JSON (`null`, `true`, `-1`, `[]`, `""`), it is sent as that
  JSON value. This is how wrong types are tested.
- Anything else is sent as plain text.

## Run the tests

```bash
pytest
```
