"""
Main Orchestrator — LangGraph Multi-Agent Valuation Pipeline.

Architecture (Planner → Executor → Critic):
  1. Data Collection Agent  — Phase A: gathers financial, market, macro, news data
  2. Valuation Agent        — Phase B: runs DCF + Comparable Multiples
  3. Validation Agent       — Phase D: consistency checks, evidence audit
  4. Critic Agent (Bonus)   — Forces Analyst to revise via LLM critique
  5. Report Agent           — Phase C: structured memo output

All financial calculations are deterministic Python.
LLM is used ONLY for: news sentiment, narrative critique, report polish.

Usage:
    python main.py                    # Run for all 20 tickers
    python main.py AAPL MSFT NVDA     # Run for specific tickers
"""
import sys
import os
import json
import logging
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Callable, Dict, List, TypedDict

import requests

# ── Imports ─────────────────────────────────────────────────────────────────
from config import (
    FRED_API_KEY, GEMINI_API_KEY, TARGET_TICKERS,
    DCF_FORECAST_YEARS, SENSITIVITY_STEP_BP, LLM_MODEL
)
from data_collection.market_data import MarketDataCollector
from data_collection.financial_statements import FinancialStatementsExtractor
from data_collection.macro_data import MacroDataCollector
from data_collection.context_data import ContextDataCollector
from data_collection.data_validation import CollectedDataValidator
from data_collection.peer_finder import PeerFinder
from valuation_engine.wacc_calculator import WACCCalculator
from valuation_engine.dcf_model import DCFModel
from valuation_engine.comparable_multiples import ComparableMultiples
from valuation_engine.sensitivity import SensitivityAnalysis
from validation.validator import ValuationValidator
from validation.revisor import RevisorAgent
from report_generator.memo_builder import MemoBuilder
from backtesting.historical_compare import HistoricalBacktester

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
MAX_REVISIONS = 1
DATA_COLLECTION_BUDGET_SECONDS = 10.0
DEMO_TICKERS = {"AAPL", "MSFT", "NVDA", "GOOGL"}
COLLECTION_EXCEPTIONS = (
    requests.RequestException,
    TimeoutError,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    OSError,
)
VALUATION_EXCEPTIONS = (
    requests.RequestException,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    RuntimeError,
    OSError,
)
VALIDATION_EXCEPTIONS = (
    requests.RequestException,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    RuntimeError,
    OSError,
    ImportError,
)


# ── LangGraph State ─────────────────────────────────────────────────────────
class AgentState(TypedDict):
    ticker: str
    market_data: Dict
    financial_summary: Dict
    macro_data: Dict
    collection_validation: Dict
    news_data: Dict
    context_data: Dict
    peers: List[Dict]
    peer_analysis: Dict
    dcf_result: Dict
    comparable_result: Dict
    sensitivity_data: Dict
    validation_result: Dict
    backtest_result: Dict
    llm_critique: str
    pass_validation: bool
    revisor_instructions: str
    revision_count: int
    planner_log: str
    revisor_log: str
    report_json: str
    report_markdown: str
    errors: List[str]


# ── Node Functions ──────────────────────────────────────────────────────────

def node_plan(state: AgentState) -> Dict:
    """Phase 0: Planner — defines tasks, sources, and methodologies."""
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Phase 0: Planner initializing...")
    
    plan_text = (
        f"Task Decomposition for {ticker}:\n"
        "1. Collect 5-yr financials, market multiples, and context via API.\n"
        "2. Find >=6 peers for relative valuation.\n"
        "3. Run Two-Stage UFCF DCF.\n"
        "4. Run Comparable Multiples.\n"
        "5. Critic checks constraints (g <= GDP, Margins <= 1).\n"
        "6. Revision loop if needed (max 3 times)."
    )
    return {"planner_log": plan_text}


def node_collect_data(state: AgentState) -> Dict:
    """Phase A with a 10-second total budget and partial-result collection."""
    ticker = state["ticker"]
    errors = []
    logger.info(f"[{ticker}] Phase A: Collecting data with parallel partial-result collection...")
    deadline = time.monotonic() + DATA_COLLECTION_BUDGET_SECONDS

    market_data = {}
    financial_summary = {}
    macro_data = {}
    collection_validation = {"passed": False, "rules": [], "errors": []}
    news_data = {}
    context_data = {}
    peers = []
    peer_analysis = {"warning": None, "selected_peers": [], "selection_log": []}

    def collect_market():
        return MarketDataCollector(ticker).get_market_data()

    def collect_financials():
        return FinancialStatementsExtractor(ticker).get_financial_summary()

    macro_collector = MacroDataCollector(FRED_API_KEY)

    def collect_macro():
        return macro_collector.get_macro_summary()

    def collect_news():
        collector = ContextDataCollector(ticker)
        recent_news = collector.get_recent_news(count=5)
        return {
            "recent_news": recent_news,
            "sentiment_analysis": None,
            "data_source": "Yahoo Finance news",
        }

    def collect_business_description():
        return ContextDataCollector(ticker).get_business_description()

    def collect_recent_filings():
        collector = ContextDataCollector(ticker)
        filings = collector.get_recent_filings(count=5)
        calls = collector.build_call_excerpts(filings)
        return {
            "filing_excerpts": filings,
            "call_excerpts": calls,
        }

    def collect_peers():
        finder = PeerFinder(ticker)
        # Peer collection is one of the slowest parts of Phase A. Give it the full
        # remaining wall-clock budget once the core valuation inputs are available.
        # This lets comparable-company collection progress in parallel with
        # contextual evidence instead of waiting behind macro/news/filing jobs.
        remaining = max(1.5, deadline - time.monotonic())
        found = finder.find_peers(max_seconds=min(9.5, remaining))
        return found, finder.last_run

    def apply_result(name: str, result) -> None:
        nonlocal market_data, financial_summary, macro_data, news_data, peers, peer_analysis
        if name == "market":
            market_data = result
        elif name == "financials":
            financial_summary = result
        elif name == "macro":
            macro_data = result
        elif name == "news":
            news_data = result
            context_data["recent_news"] = result.get("recent_news", [])
        elif name == "business_description":
            context_data["business_description"] = result
        elif name == "filings":
            context_data["filing_excerpts"] = result.get("filing_excerpts", [])
            context_data["call_excerpts"] = result.get("call_excerpts", [])
        elif name == "peers":
            peers, peer_analysis = result

    def mark_timeout(name: str) -> None:
        nonlocal macro_data, peer_analysis, context_data
        if name == "macro":
            snapshot = macro_collector.get_snapshot_summary()
            if snapshot:
                macro_data = snapshot
                errors.append("Macro data live collection timed out; local snapshot used.")
                return
        if name == "peers":
            peer_analysis = peer_analysis or {
                "warning": "Peer data temporarily unavailable due to upstream/proxy timeout.",
                "selected_peers": peers,
                "selection_log": [],
            }
        elif name in {"business_description", "filings"}:
            context_data = {
                "warning": "Contextual evidence temporarily unavailable due to upstream/proxy timeout.",
                "business_description": context_data.get("business_description", {}),
                "recent_news": context_data.get("recent_news", []),
                "filing_excerpts": context_data.get("filing_excerpts", []),
                "call_excerpts": context_data.get("call_excerpts", []),
            }
        errors.append(f"{name.capitalize()} temporarily unavailable due to upstream/proxy timeout.")

    def run_job_batch(jobs: Dict[str, Callable], max_workers: int) -> None:
        executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_map = {executor.submit(job): name for name, job in jobs.items()}
            pending = set(future_map.keys())
            while pending and time.monotonic() < deadline:
                done, pending = wait(
                    pending,
                    timeout=max(0.0, deadline - time.monotonic()),
                    return_when=FIRST_COMPLETED,
                )
                if not done:
                    break
                for future in done:
                    name = future_map[future]
                    try:
                        apply_result(name, future.result())
                    except COLLECTION_EXCEPTIONS as e:
                        logger.warning("[%s] %s collection failed: %s", ticker, name, e)
                        errors.append(f"{name.capitalize()} temporarily unavailable due to upstream/proxy timeout: {e}")

            for future in pending:
                name = future_map[future]
                if future.done():
                    try:
                        apply_result(name, future.result())
                        continue
                    except COLLECTION_EXCEPTIONS as e:
                        logger.warning("[%s] %s collection completed with error during timeout handling: %s", ticker, name, e)
                        errors.append(f"{name.capitalize()} temporarily unavailable due to upstream/proxy timeout: {e}")
                        continue
                future.cancel()
                mark_timeout(name)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    core_jobs = {
        "market": collect_market,
        "financials": collect_financials,
        "macro": collect_macro,
        "peers": collect_peers,
    }
    run_job_batch(core_jobs, max_workers=4)

    supplemental_jobs = {
        "news": collect_news,
        "business_description": collect_business_description,
        "filings": collect_recent_filings,
    }
    if time.monotonic() < deadline:
        # Contextual evidence is lower priority than macro inputs and peer data.
        run_job_batch(supplemental_jobs, max_workers=3)

    collection_validation = CollectedDataValidator(
        ticker=ticker,
        market_data=market_data,
        financial_summary=financial_summary,
        macro_data={
            **macro_data,
            "terminal_growth_anchor": macro_data.get("long_term_gdp_growth"),
        },
    ).run()
    if not collection_validation.get("passed"):
        errors.extend(collection_validation.get("errors", []))
        logger.warning(
            "[%s] Data validation failed before valuation: %s",
            ticker,
            collection_validation.get("errors"),
        )

    context_data.setdefault("business_description", {})
    context_data.setdefault("recent_news", news_data.get("recent_news", []))
    context_data.setdefault("filing_excerpts", [])
    context_data.setdefault("call_excerpts", [])

    elapsed = DATA_COLLECTION_BUDGET_SECONDS - max(0.0, deadline - time.monotonic())
    logger.info(f"[{ticker}] Phase A complete in {elapsed:.2f}s. Collected {len(peers)} peers.")
    return {
        "market_data": market_data,
        "financial_summary": financial_summary,
        "macro_data": macro_data,
        "collection_validation": collection_validation,
        "news_data": news_data,
        "context_data": context_data,
        "peers": peers,
        "peer_analysis": peer_analysis,
        "errors": errors,
    }


def node_run_valuation(state: AgentState) -> Dict:
    """Phase B: Valuation — deterministic DCF + Comparable Multiples."""
    ticker = state["ticker"]
    errors = list(state.get("errors", []))
    logger.info(f"[{ticker}] Phase B: Running valuation...")

    dcf_result = {}
    comparable_result = {}
    sensitivity_data = {}

    fin = None
    macro = None

    collection_validation = state.get("collection_validation") or {}
    if collection_validation and not collection_validation.get("passed", True):
        errors.append("Valuation blocked because required collected inputs failed validation.")
        logger.error("[%s] Phase B blocked by invalid collected inputs.", ticker)
        return {
            "dcf_result": dcf_result,
            "comparable_result": comparable_result,
            "sensitivity_data": sensitivity_data,
            "errors": errors,
        }

    # DCF Model
    try:
        fin = FinancialStatementsExtractor(ticker)
        macro = MacroDataCollector(FRED_API_KEY)
        wacc_calc = WACCCalculator(ticker, macro, fin)
        dcf = DCFModel(ticker, macro, fin, wacc_calc, DCF_FORECAST_YEARS)
        dcf_result = dcf.run()
        logger.info(f"[{ticker}] DCF fair price: ${dcf_result.get('fair_price_per_share', 0):.2f}")
    except VALUATION_EXCEPTIONS as e:
        errors.append(f"DCF error: {e}")
        logger.error(f"[{ticker}] DCF failed: {e}")

    # Comparable Multiples
    try:
        peers = state.get("peers", [])
        company_info = {
            **(state.get("market_data", {}) or {}),
            **(state.get("financial_summary", {}) or {}),
            **(getattr(fin, "info", {}) if fin is not None else {}),
        }
        if peers and company_info:
            comp = ComparableMultiples(ticker, peers, company_info)
            comparable_result = comp.calculate()
            logger.info(f"[{ticker}] Comps fair price: ${comparable_result.get('composite_fair_price', 0):.2f}")
    except VALUATION_EXCEPTIONS as e:
        errors.append(f"Comparables error: {e}")
        logger.warning(f"[{ticker}] Comparable valuation failed: {e}")

    # Sensitivity Analysis (Bonus)
    try:
        if dcf_result:
            sens = SensitivityAnalysis(dcf_result)
            sensitivity_data = sens.generate_matrix(SENSITIVITY_STEP_BP)
    except VALUATION_EXCEPTIONS as e:
        errors.append(f"Sensitivity error: {e}")
        logger.warning(f"[{ticker}] Sensitivity analysis failed: {e}")

    return {
        "dcf_result": dcf_result,
        "comparable_result": comparable_result,
        "sensitivity_data": sensitivity_data,
        "errors": errors,
    }


def node_validate(state: AgentState) -> Dict:
    """Phase D: Validation & Critique — deterministic rule-based checks."""
    ticker = state["ticker"]
    errors = list(state.get("errors", []))
    logger.info(f"[{ticker}] Phase D: Validating...")

    validation_result = {}
    backtest_result = {}
    llm_critique = ""
    revisor_instructions = ""
    pass_validation = True
    
    # Deterministic validation
    try:
        dcf = state.get("dcf_result", {})
        comp = state.get("comparable_result")
        
        # DCF is the critical path. Missing peers should reduce confidence, not block report generation.
        if not dcf:
            pass_validation = False
            revisor_instructions += "Critical missing data: DCF output unavailable. "
            logger.error(f"[{ticker}] Validation failed: Missing DCF output.")
        elif not state.get("peers"):
            logger.warning(f"[{ticker}] Peer set unavailable or rate-limited. Continue with DCF-first report generation.")
            
        validator = ValuationValidator(
            dcf_result=dcf,
            comparable_result=comp,
            financial_summary=state.get("financial_summary", {}),
            market_data=state.get("market_data", {}),
        )
        validation_result = validator.run_full_validation()
        conf = validation_result.get("confidence_score", 0)
        logger.info(f"[{ticker}] Confidence: {conf}/10")
        
        # If strict deterministic rules fail or confidence < 8, force retries
        if dcf and conf < 8 and state.get("revision_count", 0) < MAX_REVISIONS:
            pass_validation = False
            revisor_instructions += f"Confidence {conf} is too low. Revise assumptions. "
            logger.warning(f"[{ticker}] Confidence too low, routing to Revisor.")

        # LLM Critic Agent
        if GEMINI_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model=LLM_MODEL, temperature=0,
                    google_api_key=GEMINI_API_KEY
                )
                llm_critique = validator.generate_llm_critique(llm)
                # LLM can also flag pass/fail in the text
                if "【FAIL】" in llm_critique or "REVISE" in llm_critique.upper():
                    if state.get("revision_count", 0) < MAX_REVISIONS:
                        pass_validation = False
                        revisor_instructions += "LLM Critic demanded revision. "
            except VALIDATION_EXCEPTIONS as e:
                llm_critique = f"LLM critique unavailable: {e}"
                logger.warning(f"[{ticker}] LLM critique unavailable: {e}")
    except VALIDATION_EXCEPTIONS as e:
        errors.append(f"Validation error: {e}")
        pass_validation = False
        logger.error(f"[{ticker}] Validation failed: {e}")

    # Historical Backtesting (Bonus)
    try:
        dcf = state.get("dcf_result", {})
        if dcf:
            bt = HistoricalBacktester(ticker)
            backtest_result = bt.run_backtest(dcf)
    except VALIDATION_EXCEPTIONS as e:
        errors.append(f"Backtesting error: {e}")
        logger.warning(f"[{ticker}] Backtesting failed: {e}")

    # Fallback to prevent infinite loop
    if state.get("revision_count", 0) >= MAX_REVISIONS:
        pass_validation = True
        logger.warning(f"[{ticker}] Max revisions reached. Forcing report generation.")

    return {
        "validation_result": validation_result,
        "backtest_result": backtest_result,
        "llm_critique": llm_critique,
        "pass_validation": pass_validation,
        "revisor_instructions": revisor_instructions,
        "errors": errors,
    }


def node_revise(state: AgentState) -> Dict:
    """Phase D: Revisor Agent — adjusts inputs if validation fails."""
    revisor = RevisorAgent(state)
    return revisor.revise()


def node_generate_report(state: AgentState) -> Dict:
    """Phase C: Structured Output — JSON + Markdown valuation memo."""
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Phase C: Generating report...")

    memo = MemoBuilder(
        ticker=ticker,
        dcf_result=state.get("dcf_result", {}),
        comparable_result=state.get("comparable_result"),
        peer_analysis=state.get("peer_analysis"),
        validation_result=state.get("validation_result"),
        market_data=state.get("market_data"),
        financial_summary=state.get("financial_summary"),
        news_data=state.get("news_data"),
        context_data=state.get("context_data"),
        sensitivity_data=state.get("sensitivity_data"),
        backtesting_data=state.get("backtest_result"),
        llm_critique=state.get("llm_critique"),
        pipeline_errors=state.get("errors", []),
    )
    return {
        "report_json": memo.to_json(),
        "report_markdown": memo.to_markdown(),
    }


# ── Pipeline Execution ──────────────────────────────────────────────────────

def run_valuation_pipeline(ticker: str) -> AgentState:
    """
    Execute the full valuation pipeline for a single ticker.
    Uses sequential node execution (equivalent to a LangGraph linear graph).
    Architecture: Data Collection → Valuation → Validation → Report
    """
    logger.info(f"{'='*60}")
    logger.info(f"Starting valuation pipeline for {ticker}")
    logger.info(f"{'='*60}")

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

    # Sequential approximation of the graph
    state.update(node_plan(state))
    state.update(node_collect_data(state))
    state.update(node_run_valuation(state))
    state.update(node_validate(state))
    
    # Loop manually up to 3 times
    while not state.get("pass_validation") and state.get("revision_count", 0) < MAX_REVISIONS:
        state.update(node_revise(state))
        state.update(node_run_valuation(state))
        state.update(node_validate(state))
        
    state.update(node_generate_report(state))

    # Save outputs
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, f"{ticker}_valuation.json")
    md_path = os.path.join(output_dir, f"{ticker}_valuation.md")

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(state["report_json"])
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(state["report_markdown"])

    logger.info(f"[{ticker}] Reports saved to {output_dir}/")

    if state["errors"]:
        logger.warning(f"[{ticker}] Completed with {len(state['errors'])} errors:")
        for err in state["errors"]:
            logger.warning(f"  - {err}")
    else:
        logger.info(f"[{ticker}] Completed successfully!")

    return state


def route_after_validation(state: AgentState) -> str:
    """Conditional edge routing based on Critic validation."""
    if state.get("pass_validation"):
        return "generate_report"
    else:
        if state.get("revision_count", 0) >= MAX_REVISIONS:
            return "generate_report"
        return "revisor"

def run_langgraph_pipeline(ticker: str) -> AgentState:
    """
    LangGraph-based pipeline with full conditional closed-loop.
    Planner → Data → Valuator → Critic → {Revisor|Reporter}
    """
    try:
        from langgraph.graph import StateGraph, END

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("planner", node_plan)
        workflow.add_node("collect_data", node_collect_data)
        workflow.add_node("run_valuation", node_run_valuation)
        workflow.add_node("validate", node_validate)
        workflow.add_node("revisor", node_revise)
        workflow.add_node("generate_report", node_generate_report)

        # Define edges: conditional graph
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "collect_data")
        workflow.add_edge("collect_data", "run_valuation")
        workflow.add_edge("run_valuation", "validate")
        
        # Conditional Edges from validate
        workflow.add_conditional_edges(
            "validate",
            route_after_validation,
            {
                "generate_report": "generate_report",
                "revisor": "revisor"
            }
        )
        
        workflow.add_edge("revisor", "run_valuation") # The closed loop
        workflow.add_edge("generate_report", END)

        # Compile and run
        app = workflow.compile()
        initial_state: AgentState = {
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
        result = app.invoke(initial_state)

        # Save outputs
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, f"{ticker}_valuation.json"), "w", encoding="utf-8") as f:
            f.write(result["report_json"])
        with open(os.path.join(output_dir, f"{ticker}_valuation.md"), "w", encoding="utf-8") as f:
            f.write(result["report_markdown"])
        return result

    except ImportError:
        logger.warning("LangGraph not installed. Falling back to sequential pipeline.")
        return run_valuation_pipeline(ticker)


# ── Main Entry ──────────────────────────────────────────────────────────────

def main():
    """
    Entry point. Accepts optional ticker arguments.
    Usage:
        python main.py                    # All 20 tickers
        python main.py AAPL MSFT NVDA     # Specific tickers
    """
    if len(sys.argv) > 1:
        tickers = [t.upper() for t in sys.argv[1:]]
    else:
        tickers = TARGET_TICKERS

    logger.info(f"AI Valuation Agent — Processing {len(tickers)} companies")
    logger.info(f"Tickers: {', '.join(tickers)}")

    results = {}
    for ticker in tickers:
        try:
            state = run_langgraph_pipeline(ticker)
            results[ticker] = {
                "status": "success",
                "fair_price": state.get("dcf_result", {}).get("fair_price_per_share"),
                "confidence": state.get("validation_result", {}).get("confidence_score"),
                "errors": state.get("errors", []),
            }
        except VALIDATION_EXCEPTIONS as e:
            logger.exception(f"[{ticker}] Pipeline failed: {e}")
            results[ticker] = {"status": "failed", "error": str(e)}

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("VALUATION SUMMARY")
    logger.info(f"{'='*60}")
    for ticker, r in results.items():
        if r["status"] == "success":
            fp = r.get("fair_price", "N/A")
            conf = r.get("confidence", "N/A")
            logger.info(f"  {ticker}: Fair Price = ${fp}, Confidence = {conf}/10")
        else:
            logger.info(f"  {ticker}: FAILED — {r.get('error', 'Unknown')}")

    # Save summary
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    summary_path = os.path.join(output_dir, "valuation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    main()
