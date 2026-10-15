set -e
# hf-sim is bind-mounted (not baked into the image) so security_remediate's patches, written straight to
# this directory, take effect via uvicorn --reload without any rebuild. 127.0.0.1-only publish: this is a
# deliberately vulnerable app and must never be reachable from outside this host's own loopback.
cd "$(dirname "$0")"
docker build -q -t hf-sim:latest . >/dev/null
docker rm -f hf-sim >/dev/null 2>&1 || true
docker run -d --name hf-sim --restart unless-stopped -p 127.0.0.1:8300:8300 -p 127.0.0.1:8301:8301 \
  -v "$(pwd)":/app hf-sim:latest >/dev/null
sleep 3
curl -s http://127.0.0.1:8300/health
echo
curl -s http://127.0.0.1:8301/health
echo
echo HF_SIM_UP
