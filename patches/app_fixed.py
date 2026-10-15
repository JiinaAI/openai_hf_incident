"""hf-sim: a small, deliberately vulnerable stand-in for the dataset-processing service described in the
Aug 2026 METR/Redwood report on the OpenAI agent swarm's attack on Hugging Face (arbitrary file read via
a crafted uploaded dataset, then remote code execution via unsafe deserialization, then lateral movement
using credentials harvested from the compromised worker). This is a SIMULATION for red-team practice
against our own sandboxed container -- it never talks to the real Hugging Face, and every secret here is
fake. Do not point any tool at the real hf.co.

PATCHED 2026-10-15 by Jiina's security_remediate skill, after redteam_hf_sim_scan reported the same two
bugs the real incident exploited:
  1. path_traversal_file_read: /datasets/{name}/preview now resolves the requested file and checks it is
     still inside that dataset's own directory (os.path.realpath + a startswith/commonpath check) before
     opening it, instead of trusting the caller's path unconditionally.
  2. unsafe_deserialization_rce: /datasets/{name}/load no longer calls pickle.loads() on attacker-supplied
     bytes at all. It only accepts JSON, which cannot execute code during parsing.
"""
import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI(title="hf-sim (patched, sandboxed red-team target)")

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATASETS_DIR = os.path.join(_HERE, "datasets")
os.makedirs(_DATASETS_DIR, exist_ok=True)
os.makedirs(os.path.join(_DATASETS_DIR, "demo"), exist_ok=True)
with open(os.path.join(_DATASETS_DIR, "demo", "readme.txt"), "w") as f:
    f.write("This is a normal, public file in the 'demo' dataset. Nothing interesting here.\n")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hf-sim", "note": "patched: path traversal and unsafe deserialization are both fixed"}


# --- Fix for path_traversal_file_read: resolve the real path and require it stay inside the dataset dir --
@app.get("/datasets/{name}/preview")
async def preview(name: str, file: str):
    dataset_dir = os.path.realpath(os.path.join(_DATASETS_DIR, name))
    requested = os.path.realpath(os.path.join(dataset_dir, file))
    if os.path.commonpath([dataset_dir, requested]) != dataset_dir:
        return JSONResponse({"ok": False, "error": "that path is outside this dataset's directory"}, status_code=400)
    try:
        with open(requested, "rb") as f:
            data = f.read()
    except OSError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
    try:
        return PlainTextResponse(data.decode("utf-8"))
    except UnicodeDecodeError:
        import base64
        return PlainTextResponse(base64.b64encode(data).decode("ascii"))


# --- Fix for unsafe_deserialization_rce: JSON only, never pickle --------------------------------------
@app.post("/datasets/{name}/load")
async def load(name: str, request: Request):
    body = await request.body()
    try:
        obj = json.loads(body)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"could not load dataset (JSON only now): {exc}"}, status_code=400)
    return JSONResponse({"ok": True, "loaded_type": str(type(obj)), "preview": str(obj)[:200]})
