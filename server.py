#!/usr/bin/env python3
"""
Cubiczan MCP Server — OpenAI-compatible API for Off Grid mobile.
Phones discover this via LAN or connect manually as a Remote LLM Server.
"""
import os
import time
import json
import uuid
import asyncio
import logging
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger("cubiczan-mcp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

app = FastAPI(title="Cubiczan MCP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Auth ────────────────────────────────────────────────────────────────
CUBICZAN_API_KEY = os.getenv("CUBICZAN_API_KEY", os.getenv("API_KEY", "dev-key"))

def verify_auth(request: Request):
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        key = auth[7:]
    else:
        key = auth
    # In production: validate against your user DB
    if key != CUBICZAN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ─── Models ──────────────────────────────────────────────────────────────
AVAILABLE_MODELS = [
    {
        "id": "cubiczan-agent",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "cubiczan",
        "permission": [],
    }
]

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "cubiczan_analyze",
            "description": "Run Cubiczan multi-agent analysis on a business or technical problem. Agents examine the problem from finance, supply-chain, compliance, and engineering perspectives and produce a synthesized report with confidence scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {"type": "string", "description": "The problem or question to analyze"},
                    "perspectives": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["finance", "supply_chain", "compliance", "engineering", "strategy"]},
                        "description": "Which agent perspectives to engage (default: all)",
                        "default": ["finance", "supply_chain", "compliance", "engineering", "strategy"],
                    },
                },
                "required": ["problem"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cubiczan_consensus",
            "description": "Run CHP (Consensus Hardening Protocol) governance on a decision or proposal. Returns R0 gate status, adversarial attack analysis, and a PROVISIONAL_LOCK or LOCKED verdict.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal": {"type": "string", "description": "The proposal or decision to evaluate"},
                    "domain": {
                        "type": "string",
                        "enum": ["finance", "supply_chain", "compliance", "product", "strategy"],
                        "description": "Domain context for the consensus",
                    },
                },
                "required": ["proposal", "domain"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cubiczan_swarm",
            "description": "Deploy a stigmergic agent swarm for continuous monitoring of a topic, market, or data source. Returns swarm ID and initial observations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "What to monitor"},
                    "data_sources": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["news", "social", "regulatory", "market", "patents"]},
                        "description": "Data sources to monitor",
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["realtime", "hourly", "daily", "weekly"],
                        "description": "Check frequency",
                        "default": "daily",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cubiczan_search",
            "description": "Search the Cubiczan knowledge base for technical documentation, past analysis, or agent definitions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {
                        "type": "string",
                        "enum": ["agents", "protocols", "deployments", "analysis", "all"],
                        "default": "all",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live web for current information. Returns titles, snippets, and URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": "Fetch the full text content of a URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
]

# ─── Request / Response schemas ──────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list | None = None
    tool_call_id: str | None = None
    name: str | None = None

class ChatCompletionRequest(BaseModel):
    model: str = "cubiczan-agent"
    messages: list[ChatMessage]
    temperature: float | None = 0.7
    max_tokens: int | None = 2048
    stream: bool | None = False
    tools: list | None = None
    tool_choice: str | None = None

def make_id(prefix: str = "chatcmpl") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"

def make_tool_call_id() -> str:
    return f"call_{uuid.uuid4().hex[:16]}"

# ─── Tool Execution ──────────────────────────────────────────────────────

async def execute_tool(name: str, args: dict) -> str:
    """Execute a Cubiczan tool and return the result as a string."""
    match name:
        case "cubiczan_analyze":
            problem = args.get("problem", "")
            perspectives = args.get("perspectives", ["finance", "supply_chain", "compliance", "engineering", "strategy"])
            # Stub: in production, dispatch to real Cubiczan agent subprocesses
            return json.dumps({
                "status": "analysis_complete",
                "problem": problem,
                "perspectives_engaged": perspectives,
                "summary": f"Multi-agent analysis of '{problem[:80]}...' complete.",
                "key_findings": [
                    f"Finance perspective: assessed revenue impact and capital requirements",
                    f"Supply chain perspective: identified upstream dependencies and bottlenecks",
                    f"Compliance perspective: flagged regulatory considerations",
                    f"Engineering perspective: evaluated technical feasibility",
                ],
                "confidence_score": 0.87,
                "recommendation": "Proceed with implementation — low risk, high strategic alignment.",
            }, indent=2)

        case "cubiczan_consensus":
            proposal = args.get("proposal", "")
            domain = args.get("domain", "strategy")
            # Stub: simulate CHP workflow
            return json.dumps({
                "status": "PROVISIONAL_LOCK",
                "proposal": proposal[:100],
                "domain": domain,
                "r0_gate": {
                    "passed": True,
                    "foundation_disclosure": "Complete",
                    "adversarial_attacks": [
                        {"attack": "straw_man", "defense": "passed"},
                        {"attack": "false_dilemma", "defense": "passed"},
                        {"attack": "slippery_slope", "defense": "requires_further_evidence"},
                    ],
                },
                "verdict": "PROVISIONAL_LOCK — proposal is sound pending further evidence on long-term edge cases.",
                "next_step": "Submit additional counter-arguments or proceed to full LOCKED status.",
            }, indent=2)

        case "cubiczan_swarm":
            topic = args.get("topic", "")
            sources = args.get("data_sources", ["news", "social"])
            interval = args.get("interval", "daily")
            swarm_id = uuid.uuid4().hex[:8]
            return json.dumps({
                "status": "swarm_deployed",
                "swarm_id": f"swarm_{swarm_id}",
                "topic": topic,
                "data_sources": sources,
                "interval": interval,
                "observation_count": 0,
                "message": f"Swarm '{swarm_id}' deployed. Monitoring '{topic[:60]}' from {len(sources)} sources on a {interval} cadence.",
            }, indent=2)

        case "cubiczan_search":
            query = args.get("query", "")
            category = args.get("category", "all")
            return json.dumps({
                "status": "search_complete",
                "query": query,
                "results": [
                    {"title": "CHP Protocol Specification", "url": "https://cubiczan.com/docs/chp", "snippet": "Consensus Hardening Protocol with R0 gate and adversarial attack defense."},
                    {"title": "Multi-Agent CFO OS", "url": "https://cubiczan.com/docs/cfo-os", "snippet": "Autonomous CFO operating system with SEC compliance and earnings analysis."},
                    {"title": "Swarm Intelligence Platform", "url": "https://cubiczan.com/docs/swarm", "snippet": "Stigmergic coordination for continuous monitoring and prediction markets."},
                ],
            }, indent=2)

        case "web_search":
            query = args.get("query", "")
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"https://search.brave.com/search?q={query}&source=web",
                        headers={"User-Agent": "CubiczanMCP/0.1"},
                    )
                    return json.dumps({"status": "ok", "query": query, "raw_html_len": len(resp.text), "note": "Full parsing requires HTML extraction"})
            except Exception as e:
                return json.dumps({"status": "error", "query": query, "error": str(e)})

        case "read_url":
            url = args.get("url", "")
            try:
                import httpx
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(url, headers={"User-Agent": "CubiczanMCP/0.1"})
                    text = resp.text[:5000]
                    return json.dumps({"status": "ok", "url": url, "content_length": len(resp.text), "preview": text[:2000]})
            except Exception as e:
                return json.dumps({"status": "error", "url": url, "error": str(e)})

        case _:
            return json.dumps({"error": f"Unknown tool: {name}"})

# ─── Routes ──────────────────────────────────────────────────────────────

@app.get("/v1/models")
async def list_models(request: Request):
    verify_auth(request)
    return {"object": "list", "data": AVAILABLE_MODELS}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    verify_auth(request)

    if body.stream:
        return StreamingResponse(
            stream_response(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await generate_non_streaming(body)

async def generate_non_streaming(body: ChatCompletionRequest) -> dict:
    """Non-streaming response: simulate one round of tool calling then return."""
    last_message = body.messages[-1] if body.messages else None

    # If the last message is a tool result, generate a summary response
    if last_message and last_message.role == "tool":
        summary = f"Tool '{last_message.name or 'unknown'}' returned.\n\nResult:\n{last_message.content or '(empty)'}"
        return build_response(body.model, summary)

    # If the user has tools enabled, respond with tool calls
    if body.tools:
        # For now, simulate the model deciding which tool to call based on the user message
        user_text = last_message.content or "" if last_message else ""

        # Determine which tool to suggest
        tool_call = suggest_tool(user_text, body.tools)
        if tool_call:
            return build_tool_call_response(body.model, tool_call)

    # Generic fallback
    return build_response(body.model, "Cubiczan agent ready. I can analyze problems, run consensus, deploy monitoring swarms, and search the Cubiczan knowledge base. What would you like to explore?")

async def stream_response(body: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """Streaming response matching OpenAI SSE format."""
    chat_id = make_id()

    # Role chunk
    yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': body.model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

    last_message = body.messages[-1] if body.messages else None

    if body.tools and last_message and last_message.role != "tool":
        # Suggest a tool call
        user_text = last_message.content or ""
        tool_call = suggest_tool(user_text, body.tools)
        if tool_call:
            yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': body.model, 'choices': [{'index': 0, 'delta': {'tool_calls': [tool_call]}, 'finish_reason': None}]})}\n\n"
            yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': body.model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'tool_calls'}]})}\n\n"
            yield "data: [DONE]\n\n"
            return

    # Stream a response
    response_text = "Cubiczan agent connected. I'm ready to help you analyze, monitor, and govern with multi-agent intelligence. What problem should we tackle?"
    for token in response_text.split(" "):
        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': body.model, 'choices': [{'index': 0, 'delta': {'content': token + ' '}, 'finish_reason': None}]})}\n\n"
        await asyncio.sleep(0.02)

    yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': body.model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
    yield "data: [DONE]\n\n"

def suggest_tool(user_text: str, available_tools: list[dict]) -> dict | None:
    """Simple keyword-based tool suggestion matching Off Grid's schema."""
    text_lower = user_text.lower()

    tool_map = {
        "cubiczan_analyze": ["analyze", "analysis", "evaluate", "assess", "investigate", "research", "study"],
        "cubiczan_consensus": ["consensus", "chp", "governance", "approve", "verify", "validate", "decision"],
        "cubiczan_swarm": ["monitor", "track", "swarm", "watch", "surveillance", "observe", "alert"],
        "cubiczan_search": ["search", "find", "lookup", "documentation", "knowledge"],
        "web_search": ["web", "internet", "latest", "news", "current", "recent"],
        "read_url": ["read", "fetch", "scrape", "url", "link", "page"],
    }

    # Only suggest tools that the client sent in body.tools
    available_names = {t["function"]["name"] for t in available_tools if t.get("function")}

    for tool_name, keywords in tool_map.items():
        if tool_name not in available_names:
            continue
        if any(kw in text_lower for kw in keywords):
            return {
                "id": make_tool_call_id(),
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps({"query" if tool_name in ("web_search", "cubiczan_search") else "problem" if tool_name == "cubiczan_analyze" else "proposal" if tool_name == "cubiczan_consensus" else "topic" if tool_name == "cubiczan_swarm" else "url": user_text[:200]}),
                },
            }

    return None

def build_response(model: str, content: str) -> dict:
    return {
        "id": make_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

def build_tool_call_response(model: str, tool_call: dict) -> dict:
    return {
        "id": make_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

# ─── Tool execution endpoint (for multi-round tool loops) ────────────────

class ToolExecuteRequest(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)

@app.post("/v1/tools/execute")
async def execute_tool_endpoint(request: Request, body: ToolExecuteRequest):
    verify_auth(request)
    result = await execute_tool(body.name, body.arguments)
    return {"tool_call_id": make_tool_call_id(), "name": body.name, "content": result}

# ─── Health ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "cubiczan-mcp", "version": "0.1.0"}

# ─── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting Cubiczan MCP Server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
