# Cubiczan MCP Server

Connect your Off Grid mobile app to Cubiczan's multi-agent intelligence.

## What it does

Exposes Cubiczan's agent orchestration capabilities (CHP consensus, multi-agent workflows, stigmergic coordination) as an **OpenAI-compatible API endpoint** that Off Grid phones discover via LAN or connect to manually.

## Quick Start

```bash
pip install -r requirements.txt
export CUBICZAN_API_KEY="your-key"
python server.py
```

The server starts on `0.0.0.0:8080` and implements the OpenAI `/v1/chat/completions` endpoint.

## How it works

| Off Grid Client | Cubiczan MCP Server |
|---|---|
| Remote LLM Server (OpenAI-compatible) | FastAPI serving `/v1/models` + `/v1/chat/completions` |
| Tool calling enabled | Returns function calls for Cubiczan agents |
| LAN discovery (port 8080) | Responds to HTTP probes on /v1/models |
| Secure keychain API key storage | Validates API key from Authorization header |

## Available Tools

The server exposes Cubiczan's agent capabilities as OpenAI function tools:

- `cubiczan_analyze` — Run multi-agent analysis on a problem
- `cubiczan_consensus` — Run CHP governance consensus on a proposal
- `cubiczan_swarm` — Deploy a stigmergic swarm for continuous monitoring
- `cubiczan_search` — Search Cubiczan knowledge base
- `web_search` — Real web search
- `read_url` — Fetch and summarize a URL

## Adding to Off Grid

1. Open Off Grid → Settings → Remote Servers → Add Server
2. Enter `http://<host>:8080` as the endpoint
3. Enter your Cubiczan API key
4. The model `cubiczan-agent` will appear in your model list
5. Enable tool calling in chat settings
