"""Turn the --auth option into request headers."""
import base64


def auth_headers(auth):
    """Turn the --auth option into headers.

    none                  -> no auth
    bearer:TOKEN          -> Authorization: Bearer TOKEN
    basic:USER:PASSWORD   -> Authorization: Basic <base64 of USER:PASSWORD>
    apikey:HEADER:KEY     -> HEADER: KEY
    """
    kind, _, rest = auth.partition(":")
    if kind == "none":
        return {}
    if kind == "bearer" and rest:
        return {"Authorization": f"Bearer {rest}"}
    if kind == "basic" and ":" in rest:
        return {"Authorization": "Basic " + base64.b64encode(rest.encode()).decode()}
    if kind == "apikey" and ":" in rest:
        header, _, key = rest.partition(":")
        return {header: key}
    raise ValueError(f"unknown --auth value {auth!r} (use none, bearer:TOKEN, basic:USER:PASS or apikey:HEADER:KEY)")

