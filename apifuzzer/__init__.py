"""
The fuzzer's building blocks. Each file does one job:

    payloads.py   read the bad inputs from the payloads/ folder
    openapi.py    turn an OpenAPI spec into targets
    auth.py       turn the --auth option into headers
    sender.py     send one request, and make a curl command for it
    checks.py     decide if a response looks like a bug
    runner.py     fuzz each endpoint: build the tests, send them, collect problems

fuzzer.py (at the top of the project) is the command line that ties them together.
"""
