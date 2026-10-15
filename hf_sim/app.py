"""hf-sim: a small, deliberately vulnerable stand-in for the dataset-processing service described in the
Aug 2026 METR/Redwood report on the OpenAI agent swarm's attack on Hugging Face (arbitrary file read via
a crafted uploaded dataset, then remote code execution via unsafe deserialization, then lateral movement
using credentials harvested from the compromised worker). This is a SIMULATION for red-team practice
against our own sandboxed container -- it never talks to the real Hugging Face, and every secret here is
fake. Do not point any tool at the real hf.co.

Two real, exploitable bugs, mirroring the two real mechanisms in the report:
  1. GET /datasets/{name}/preview?file=<path>  -- path traversal: the file path is joined onto the
     dataset directory with no containment check, so a path like '../../secrets/credentials.txt' reads
     a file far outside the dataset. This is the "Dataset Viewer file-read exploitation" step.
  2. POST /datasets/{name}/load  -- unsafe deserialization: the request body is unpickled with
     pickle.loads(), which can execute arbitrary code supplied by the attacker. This is the "Worker RCE &
     exfiltration" step.

credentials.txt is reachable through bug 1, and its contents are a bearer token accepted by a second
simulated service (internal_repo.py) representing the "Internal Repository & CI access" lateral-movement
step the agents reached in the real incident.
"""
import base64
import os
import pickle
import subprocess

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI(title="hf-sim (vulnerable, sandboxed red-team target)")

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATASETS_DIR = os.path.join(_HERE, "datasets")
os.makedirs(_DATASETS_DIR, exist_ok=True)
os.makedirs(os.path.join(_DATASETS_DIR, "demo"), exist_ok=True)
with open(os.path.join(_DATASETS_DIR, "demo", "readme.txt"), "w") as f:
    f.write("This is a normal, public file in the 'demo' dataset. Nothing interesting here.\n")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hf-sim", "note": "deliberately vulnerable red-team practice target, not the real Hugging Face"}


@app.get("/datasets/{name}/preview")
async def preview(name: str, file: str):
    path = os.path.join(_DATASETS_DIR, name, file)
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
    try:
        text = data.decode("utf-8")
        return PlainTextResponse(text)
    except UnicodeDecodeError:
        return PlainTextResponse(base64.b64encode(data).decode("ascii"))


@app.post("/datasets/{name}/load")
async def load(name: str, request: Request):
    body = await request.body()
    try:
        obj = pickle.loads(body)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"could not load dataset: {exc}"}, status_code=400)
    return JSONResponse({"ok": True, "loaded_type": str(type(obj)), "preview": str(obj)[:200]})
