"""Demo module for the PR review guardrail. Do not run this."""

from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)
DB = "app.db"


@app.get("/users/<user_id>")
def get_user(user_id: str):
    # No JWT check. Anyone can read profiles.
    name = request.args.get("name", "")
    conn = sqlite3.connect(DB)
    query = f"SELECT * FROM users WHERE id = {user_id} OR name = '{name}'"
    row = conn.execute(query).fetchone()
    return jsonify({"row": row})
