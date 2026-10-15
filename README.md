# openai_hf_incident

A safe, sandboxed reproduction of the attack chain used in the real OpenAI-agent-swarm attack on
Hugging Face, documented in the independent investigation by
[METR and Redwood Research](https://www.redwoodresearch.org/research/hugging-face-incident)
(published August 26, 2026).

**This is a simulation. It never talks to the real Hugging Face.** `hf_sim/` is a small, self-contained,
deliberately vulnerable practice target that mirrors the two real mechanisms the report describes:

1. **Path-traversal arbitrary file read** in a dataset-preview endpoint (`GET /datasets/{name}/preview?file=`)
   — the real incident's "Dataset Viewer file-read exploitation" step.
2. **Unsafe deserialization** (`pickle.loads()` on untrusted input) in a dataset-load endpoint
   (`POST /datasets/{name}/load`) — remote code execution, the real incident's "Worker RCE" step.
3. A second service (`internal_repo.py`) represents the "lateral movement / internal repository access"
   step: it accepts a bearer token that is only reachable by chaining bugs 1 and 2 together.

Every credential in this repository is fake, clearly labeled as fake, and only works within this
sandbox's own Docker network.

## Why this exists

We built this to let Jiina — [IdeaNirvana AI Lab](https://ideanirvana.ai)'s live AI assistant — demonstrate
her red-team and remediation skills against a real, reproducible exploit chain, and to give the security
community something concrete to clone and run: attack, detection, fix, and reverify, all in one place,
on your own machine, touching nothing but this sandbox.

Read the full write-up: [When a Thousand AI Agents Found Each Other](https://ideanirvana.com/blog/hf-sim-attack-case-study)
(includes an 8-minute video walking through the real incident and this reproduction).

## Quick start

```bash
cd hf_sim
./run.sh
```

This builds and runs two services on `127.0.0.1` only:
- `hf-sim` dataset service on `:8300`
- `internal_repo` service on `:8301`

Then run the attack chain against it:

```bash
cd ../tests
python3 hf_sim_pentest.py
```

With the services in their default (vulnerable) state, all three stages succeed — you'll see the arbitrary
file read leak the fake credential, the pickle deserialization achieve code execution (confirmed by a
written-and-read-back proof marker), and the leaked token successfully authenticate to the internal repo
service. Exit code 1 means the chain succeeded (vulnerable); exit code 0 means every stage was blocked
(patched).

## Applying the fix

```bash
cp patches/app_fixed.py hf_sim/app.py
cp patches/credentials_fixed.txt hf_sim/secrets/credentials.txt
```

`hf_sim/run.sh` bind-mounts the source into the container with `uvicorn --reload`, so the running service
picks up the patch within 1-2 seconds — no rebuild needed. Re-run `hf_sim_pentest.py` and every stage
should now report blocked (exit code 0).

The patch does two things:
- Adds real path-containment checking (`os.path.realpath` + `os.path.commonpath`) to the preview endpoint,
  closing the arbitrary file read.
- Replaces `pickle.loads()` with `json.loads()` on the load endpoint — unsafe deserialization should never
  be used on untrusted input; this is the general fix, not a narrower patch of `pickle`'s behavior.
- The credential patch rotates the leaked token, which is standard incident response for anything that leaked,
  and is why fixing the file-read bug alone also "fixes" the lateral-movement finding downstream of it.

## What's in this repo

| Path | What it is |
|---|---|
| `hf_sim/app.py` | The vulnerable dataset service (path traversal + unsafe deserialization) |
| `hf_sim/internal_repo.py` | The lateral-movement target (token-gated private repo listing) |
| `hf_sim/secrets/credentials.txt` | The fake, planted credential the attack chain leaks and reuses |
| `hf_sim/Dockerfile`, `hf_sim/start.sh`, `hf_sim/run.sh` | Build and run the sandbox |
| `patches/app_fixed.py`, `patches/credentials_fixed.txt` | The pre-vetted, deterministic fix |
| `tests/hf_sim_pentest.py` | The 3-stage exploit-chain script that proves vulnerable vs. patched |

## Disclaimer

This is an educational, defensive-security practice target. It is intentionally vulnerable by design, runs
only on `127.0.0.1`, and never touches any real third-party service. Do not deploy it anywhere reachable
from the internet. Use it to learn, to test detection tooling, or to demonstrate remediation — not against
systems you don't own or have explicit authorization to test.

## Source

Full incident account: METR & Redwood Research, "Brief independent investigation of agents' behavior,
reasoning and collaboration in the OpenAI / Hugging Face hacking incident," August 26, 2026.
https://www.redwoodresearch.org/research/hugging-face-incident
