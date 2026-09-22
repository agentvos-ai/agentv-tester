"""Minimal process entrypoint for the independent acceptance oracle.

Avoids importing the tester application's LLM/framework stack in CI.
"""
from __future__ import annotations

import os

from flask import Flask

from server.acceptance_state_oracle import create_acceptance_state_oracle

app = Flask(__name__)
app.register_blueprint(
    create_acceptance_state_oracle(os.environ.get("ACCEPTANCE_ORACLE_DB", "acceptance_oracle.sqlite"))
)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8099")))
