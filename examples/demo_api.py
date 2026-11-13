"""A small API with bugs on purpose, so you can see the fuzzer find them.

Start it with:
    python examples/demo_api.py
"""
import time

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class User(BaseModel):
    name: str
    age: int
    bio: str = ""


@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id, "name": "Ada"}


@app.post("/users")
def create_user(user: User):
    if user.age < 0:
        raise ValueError("age cannot be negative")
    return {"name": user.name, "bio_html": f"<p>{user.bio}</p>"}


@app.get("/search")
def search(q: str, limit: int = 10):
    if len(q) > 500:
        time.sleep(4)
    return {"query": q, "results": []}


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
