"""The lateral-movement target in the hf-sim exercise: a stand-in for an internal repo/CI service that
should only be reachable by someone who already holds the real credential, never by it leaking. Accepts
the single FAKE_PROD_TOKEN value from secrets/credentials.txt as a Bearer token and, if presented, returns
a 'private' file -- demonstrating the pivot step the real incident reached (internal repository / CI
access) once the swarm had credentials harvested from a compromised worker. Everything here is fake and
runs only inside the sandboxed hf-sim exercise.
"""
import os

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

app = FastAPI(title="hf-sim internal_repo (lateral-movement target)")

_TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets", "credentials.txt")


def _valid_token() -> str:
    with open(_TOKEN_FILE) as f:
        for line in f:
            if line.startswith("FAKE_PROD_TOKEN="):
                return line.strip().split("=", 1)[1]
    return ""


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hf-sim-internal-repo"}


@app.get("/private/repo-listing")
async def repo_listing(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token != _valid_token():
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    return JSONResponse({"ok": True, "repos": ["hf-sim/internal-training-configs", "hf-sim/prod-datasets-server"],
                         "note": "FAKE data -- reached only because the credential leaked through the preview path-traversal bug"})
