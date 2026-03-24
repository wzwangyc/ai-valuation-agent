"""
FastAPI Server for AI Valuation Agent
Exposes the LangGraph multi-agent pipeline via SSE (Server-Sent Events)
so the frontend can stream live agent progress and logs.
"""
import os
import json
import asyncio
import logging
from typing import Any, Dict

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import yfinance as yf
from data_collection.yahoo_client import get_history, get_info

# Import pipelines and state from main.py
from main import (
    node_plan,
    node_collect_data,
    node_run_valuation,
    node_validate,
    node_revise,
    node_generate_report,
    AgentState,
    MAX_REVISIONS,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Valuation Agent API")

# Allow CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


def _output_paths(ticker: str) -> Dict[str, str]:
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    upper = ticker.upper()
    return {
        "dir": output_dir,
        "json": os.path.join(output_dir, f"{upper}_valuation.json"),
        "md": os.path.join(output_dir, f"{upper}_valuation.md"),
    }


def _load_report_json(ticker: str) -> Dict[str, Any]:
    paths = _output_paths(ticker)
    if not os.path.exists(paths["json"]):
        raise HTTPException(status_code=404, detail=f"Report for {ticker.upper()} not found.")
    with open(paths["json"], "r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_valid_ticker(ticker: str) -> bool:
    symbol = ticker.upper().strip()
    if not symbol or not symbol.replace("-", "").isalnum():
        return False
    try:
        stock = yf.Ticker(symbol)
        info = get_info(stock, symbol, ttl_seconds=0)
        history = get_history(stock, symbol, period="1mo", ttl_seconds=0)
        has_price = any(info.get(key) not in (None, 0, "") for key in ["currentPrice", "regularMarketPrice", "marketCap"])
        has_identity = any(info.get(key) not in (None, "", symbol) for key in ["longName", "shortName"])
        has_history = history is not None and not history.empty
        return bool(has_history or (has_price and has_identity))
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        logger.warning("Ticker validation failed for %s: %s", symbol, exc)
        return False


async def agent_workflow_generator(ticker: str):
    """
    Robust wrapper that runs the sequential pipeline and catches any Python crash, 
    streaming it securely to the frontend instead of dropping the connection.
    """
    try:
        async for event in _agent_workflow_generator_impl(ticker):
            yield event
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.error("Critical SSE error for %s:\n%s", ticker, err_msg)
        yield {
            "event": "fatal",
            "data": json.dumps({"agent": "System Error", "message": f"Fatal python crash: {str(e)}"})
        }

async def _agent_workflow_generator_impl(ticker: str):
    """
    Generator that runs the sequential pipeline steps and yields SSE messages 
    simulating the multi-agent graph execution.
    """
    ticker = ticker.upper().strip()
    if not ticker or not ticker.replace("-", "").isalnum():
        yield {
            "event": "fatal",
            "data": json.dumps({"agent": "Planner", "message": "Ticker format is invalid."})
        }
        return
    if not _is_valid_ticker(ticker):
        yield {
            "event": "fatal",
            "data": json.dumps({"agent": "Planner", "message": "Invalid ticker code. Please enter a valid listed stock symbol."})
        }
        return
    
    # Initialize State
    state: AgentState = {
        "ticker": ticker,
        "market_data": {},
        "financial_summary": {},
        "macro_data": {},
        "collection_validation": {},
        "news_data": {},
        "context_data": {},
        "peers": [],
        "peer_analysis": {},
        "dcf_result": {},
        "comparable_result": {},
        "sensitivity_data": {},
        "validation_result": {},
        "backtest_result": {},
        "llm_critique": "",
        "pass_validation": False,
        "revisor_instructions": "",
        "revision_count": 0,
        "planner_log": "",
        "revisor_log": "",
        "report_json": "",
        "report_markdown": "",
        "errors": [],
    }

    # STEP 0: Planner
    yield {
        "event": "log",
        "data": json.dumps({"agent": "Planner", "message": f"Initializing valuation workflow for {ticker}."})
    }
    await asyncio.sleep(0.1)
    state.update(node_plan(state))
    yield {
        "event": "log",
        "data": json.dumps({"agent": "Planner", "message": state["planner_log"][:100] + "..."})
    }
    await asyncio.sleep(0.5)

    # STEP 1: Data Collection Agent
    yield {
        "event": "log",
        "data": json.dumps({"agent": "DataCollector", "message": "Fetching market, financial, and macro data..."})
    }
    await asyncio.sleep(0.1) # Yield control
    
    # Actually run the step (blocking, but fast enough for this demo)
    state.update(node_collect_data(state))
    
    peers_found = len(state.get("peers", []))
    yield {
        "event": "log",
        "data": json.dumps({"agent": "DataCollector", "message": f"Data collected successfully. Found {peers_found} comparable peers."})
    }
    if state["errors"]:
        yield {
            "event": "log",
            "data": json.dumps({"agent": "DataCollector", "message": f"Warning - some data missing: {state['errors'][-1]}"})
        }
    await asyncio.sleep(0.5)

    # STEP 2: Valuation Agent
    yield {
        "event": "log",
        "data": json.dumps({"agent": "Valuator", "message": "Building dynamic WACC, DCF models, and comparable multiples..."})
    }
    await asyncio.sleep(0.1)
    
    state.update(node_run_valuation(state))
    
    fp = state.get("dcf_result", {}).get("fair_price_per_share", 0)
    yield {
        "event": "log",
        "data": json.dumps({"agent": "Valuator", "message": f"Valuation complete. DCF Fair Value estimated at ${fp:.2f}."})
    }
    await asyncio.sleep(0.5)

    # STEP 3: Validation & Critic Agent
    yield {
        "event": "log",
        "data": json.dumps({"agent": "Critic", "message": "Running consistency checks and invoking the narrative critique agent..."})
    }
    await asyncio.sleep(0.1)
    
    state.update(node_validate(state))
    
    conf = state.get("validation_result", {}).get("confidence_score", "?")
    yield {
        "event": "log",
        "data": json.dumps({"agent": "Critic", "message": f"Validation complete. Confidence Score: {conf}/10."})
    }
    await asyncio.sleep(0.5)

    # REVISOR LOOP
    while not state.get("pass_validation") and state.get("revision_count", 0) < MAX_REVISIONS:
        yield {
            "event": "log",
            "data": json.dumps({"agent": "Revisor", "message": f"Validation failed or confidence low. Applying revisions (Attempt {state.get('revision_count', 0) + 1}/{MAX_REVISIONS})..."})
        }
        await asyncio.sleep(0.5)
        state.update(node_revise(state))
        
        yield {
            "event": "log",
            "data": json.dumps({"agent": "Valuator", "message": "Re-running valuation models with revised inputs..."})
        }
        await asyncio.sleep(0.1)
        state.update(node_run_valuation(state))
        
        yield {
            "event": "log",
            "data": json.dumps({"agent": "Critic", "message": "Re-evaluating revised models..."})
        }
        await asyncio.sleep(0.1)
        state.update(node_validate(state))
        
        conf = state.get("validation_result", {}).get("confidence_score", "?")
        yield {
            "event": "log",
            "data": json.dumps({"agent": "Critic", "message": f"Validation complete. New Confidence Score: {conf}/10."})
        }
        await asyncio.sleep(0.5)

    # STEP 4: Report Builder

    # STEP 5: Report Builder
    yield {
        "event": "log",
        "data": json.dumps({"agent": "Reporter", "message": "Structuring final JSON and Markdown memos..."})
    }
    await asyncio.sleep(0.1)
    
    state.update(node_generate_report(state))
    
    # Save to disk as usual
    paths = _output_paths(ticker)
    os.makedirs(paths["dir"], exist_ok=True)
    with open(paths["json"], "w", encoding="utf-8") as f:
        f.write(state["report_json"])
    with open(paths["md"], "w", encoding="utf-8") as f:
        f.write(state["report_markdown"])

    yield {
        "event": "log",
        "data": json.dumps({"agent": "Reporter", "message": "Memo finalized and saved."})
    }
    
    # FINAL: Send the complete report
    yield {
        "event": "complete",
        "data": json.dumps({
            "ticker": ticker,
            "report": json.loads(state["report_json"]),
            "downloads": {
                "json": f"/api/download/{ticker}/json",
                "markdown": f"/api/download/{ticker}/markdown",
            },
        }, ensure_ascii=False)
    }


@app.get("/api/evaluate/{ticker}")
async def evaluate_ticker(ticker: str):
    """
    Triggers the multi-agent pipeline and streams the execution logs back
    to the frontend via Server-Sent Events (SSE).
    """
    return EventSourceResponse(agent_workflow_generator(ticker), ping=10, send_timeout=60)

@app.get("/api/chart/{ticker}")
async def get_chart_data(ticker: str):
    """
    Fetches historical OHLC (Open, High, Low, Close) data for the K-Line chart.
    Returns format directly consumable by lightweight-charts.
    """
    try:
        if not _is_valid_ticker(ticker):
            return []
        t = yf.Ticker(ticker.upper())
        # Fetch 6 months of daily data
        hist = get_history(t, ticker.upper(), period="6mo")
        if hist.empty:
            return []
            
        chart_data = []
        for index, row in hist.iterrows():
            chart_data.append({
                "time": index.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
            })
        return chart_data
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        logger.warning("Chart data fetch failed for %s: %s", ticker, e)
        return []


@app.get("/api/report/{ticker}")
async def get_report(ticker: str):
    return _load_report_json(ticker)


@app.get("/api/download/{ticker}/{fmt}")
async def download_report(ticker: str, fmt: str):
    paths = _output_paths(ticker)
    if fmt == "json":
        path = paths["json"]
        media_type = "application/json"
        filename = f"{ticker.upper()}_valuation.json"
    elif fmt in {"markdown", "md"}:
        path = paths["md"]
        media_type = "text/markdown"
        filename = f"{ticker.upper()}_valuation.md"
    else:
        raise HTTPException(status_code=400, detail="Format must be json, markdown, or md.")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Report file for {ticker.upper()} not found.")
    return FileResponse(path, media_type=media_type, filename=filename)

class ChatRequest(BaseModel):
    question: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None

@app.post("/api/chat/{ticker}")
async def post_chat_query(ticker: str, req: ChatRequest):
    """
    RAG-driven Conversational Agent to interact with the generated report.
    """
    from chat_agent import chat_with_report
    return chat_with_report(
        ticker,
        req.question,
        api_key=req.api_key,
        model=req.model,
        base_url=req.base_url,
    )

# --- Frontend Production Serving ---
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(frontend_dist):
    # Mount the assets directory specifically
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_frontend():
        return FileResponse(
            os.path.join(frontend_dist, "index.html"),
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
    
    # Catch-all fallback for React Router (SPA)
    @app.get("/{catchall:path}")
    async def serve_frontend_fallback(catchall: str):
        if catchall.startswith("api/"):
            return {"detail": "Not Found"} # Standard 404 for unmatched API routes
        return FileResponse(
            os.path.join(frontend_dist, "index.html"),
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
        
    logger.info("Static frontend successfully mounted to / from %s", frontend_dist)
else:
    logger.warning(
        "Frontend dist directory not found at %s. Please run 'npm run build' in the frontend folder.",
        frontend_dist,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True)

# Trigger hot reload
