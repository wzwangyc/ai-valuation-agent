import React, { useEffect, useMemo, useRef, useState } from "react";
import { createChart, CrosshairMode, CandlestickSeries, LineSeries, LineStyle } from "lightweight-charts";

const API_BASE = "";
const PIPELINE = ["Planner", "DataCollector", "Valuator", "Critic", "Revisor", "Reporter"];
const STORAGE_KEY = "ai-valuation-terminal-api";
const TICKER_SUGGESTIONS = ["AAPL", "MSFT", "NVDA", "GOOGL"];

function readApiConfig() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function toNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value, digits = 2) {
  const num = toNumber(value);
  if (num === null) return "N/A";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(num);
}

function formatCurrency(value, digits = 2) {
  const num = toNumber(value);
  if (num === null) return "N/A";
  return `$${new Intl.NumberFormat("en-US", {
    notation: Math.abs(num) >= 1e9 ? "compact" : "standard",
    maximumFractionDigits: digits,
    minimumFractionDigits: digits > 0 && Math.abs(num) < 1000 ? digits : 0,
  }).format(num)}`;
}

function formatPlainCurrency(value, digits = 2) {
  const num = toNumber(value);
  if (num === null) return "N/A";
  return `$${formatNumber(num, digits)}`;
}

function formatPercent(value, digits = 2) {
  const num = toNumber(value);
  if (num === null) return "N/A";
  return `${formatNumber(num * 100, digits)}%`;
}

function formatMultiple(value) {
  const num = toNumber(value);
  if (num === null) return "N/A";
  return `${formatNumber(num, 2)}x`;
}

function formatDeltaPercent(value) {
  const num = toNumber(value);
  if (num === null) return "N/A";
  const prefix = num > 0 ? "+" : "";
  return `${prefix}${formatNumber(num, 1)}%`;
}

function sourceHost(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url || "Source";
  }
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

const FLOW_STAGE_BY_AGENT = {
  Planner: "input",
  DataCollector: "input",
  Valuator: "calculation",
  Critic: "decision",
  Revisor: "decision",
  Reporter: "result",
};

const PANEL_HELP = {
  "Data Availability": "Shows whether each module used live API data, fallback data, or timed out during collection.",
  "Agent Pipeline": "Summarizes the live multi-agent workflow from planning through reporting.",
  "AAPL K-Line": "Displays price action with valuation overlays, including target price and valuation range.",
  "MSFT K-Line": "Displays price action with valuation overlays, including target price and valuation range.",
  "NVDA K-Line": "Displays price action with valuation overlays, including target price and valuation range.",
  "GOOGL K-Line": "Displays price action with valuation overlays, including target price and valuation range.",
  "Report Agent": "Presents the structured valuation memo, headline assumptions, and downloadable outputs.",
  "Financial Data": "Shows the core three-statement anchors used to support the valuation model.",
  "Peer Group Analysis": "Explains comparable-company selection, peer multiples, and current-company benchmarking.",
  "Contextual Evidence": "Collects business description, filings, call excerpts, and recent news for qualitative support.",
  "DCF Calculation Modules": "Breaks the DCF model into inputs, calculations, validation checks, and final valuation outputs.",
  "Validation & Critic Mechanisms": "Shows inconsistency checks, evidence mapping, and uncertainty scoring.",
  "Pipeline Trace": "Lists timestamped agent actions so the workflow remains auditable and easy to explain.",
  "Evidence Sources": "Lists source links used by the report so each visible conclusion can be traced back.",
};

function saveApiConfig(config) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

function Panel({ title, eyebrow, actions, children, className = "", help }) {
  const helpText = help || PANEL_HELP[title];
  return (
    <section className={`terminal-panel ${className}`.trim()}>
      <div className="terminal-panel-header">
        <div>
          {eyebrow ? <p className="panel-eyebrow">{eyebrow}</p> : null}
          <h2>{title}</h2>
        </div>
        {actions || helpText ? (
          <div className="panel-actions">
            {helpText ? (
              <div className="help-badge" tabIndex={0}>
                <span>?</span>
                <div className="help-tooltip">{helpText}</div>
              </div>
            ) : null}
            {actions}
          </div>
        ) : null}
      </div>
      {children}
    </section>
  );
}

function EmptyState({ title, body }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

function ApiDrawer({ open, onClose, apiConfig, onSave }) {
  const [draft, setDraft] = useState(apiConfig);

  useEffect(() => {
    setDraft(apiConfig);
  }, [apiConfig]);

  return (
    <div className={`drawer-shell ${open ? "open" : ""}`}>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer-panel">
        <div className="drawer-header">
          <div>
            <p className="panel-eyebrow">LLM configuration</p>
            <h3>API Settings</h3>
          </div>
          <button className="button button-ghost" onClick={onClose}>Close</button>
        </div>
        <div className="drawer-stack">
          <label className="field">
            <span>Gemini / OpenAI Compatible API Key</span>
            <input
              type="password"
              value={draft.api_key || ""}
              placeholder="Paste your own API key"
              onChange={(event) => setDraft((prev) => ({ ...prev, api_key: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>API Base URL</span>
            <input
              value={draft.base_url || ""}
              placeholder="Optional for proxy or OpenAI-compatible endpoint"
              onChange={(event) => setDraft((prev) => ({ ...prev, base_url: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>Model</span>
            <select
              value={draft.model || "gemini-flash-latest"}
              onChange={(event) => setDraft((prev) => ({ ...prev, model: event.target.value }))}
            >
              <option value="gemini-flash-latest">Gemini Flash Latest</option>
              <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
            </select>
          </label>
          <div className="callout">
            <strong>Default chat path:</strong> Gemini uses the official Google endpoint automatically. Leave Base URL blank unless you are using a proxy.
          </div>
          <button className="button button-primary" onClick={() => onSave(draft)}>
            Save Configuration
          </button>
        </div>
      </aside>
    </div>
  );
}

function CandlestickPanel({ ticker, data, summary }) {
  const hostRef = useRef(null);

  useEffect(() => {
    if (!hostRef.current) return undefined;
    const chart = createChart(hostRef.current, {
      autoSize: true,
      layout: {
        background: { color: "transparent" },
        textColor: "#b8c4d9",
        fontFamily: "IBM Plex Sans, sans-serif",
      },
      crosshair: { mode: CrosshairMode.Normal },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale: { borderColor: "rgba(255,255,255,0.08)" },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#33c481",
      downColor: "#ff6b7f",
      wickUpColor: "#33c481",
      wickDownColor: "#ff6b7f",
      borderVisible: false,
    });
    if (data.length) {
      series.setData(data);
      chart.timeScale().fitContent();
    }
    const overlayConfig = [
      { price: summary?.target_price, title: "Target", color: "rgba(115,161,255,0.95)" },
      { price: summary?.valuation_range?.low, title: "Range Low", color: "rgba(255,106,128,0.95)" },
      { price: summary?.valuation_range?.high, title: "Range High", color: "rgba(50,201,135,0.95)" },
    ];
    const overlays = [];
    const firstTime = data[0]?.time;
    const lastTime = data[data.length - 1]?.time;
    overlayConfig.forEach((line) => {
      if (!firstTime || !lastTime || toNumber(line.price) === null) return;
      const overlay = chart.addSeries(LineSeries, {
        color: line.color,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        crosshairMarkerVisible: false,
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineColor: line.color,
        priceLineStyle: LineStyle.Dashed,
        title: line.title,
      });
      overlay.setData([
        { time: firstTime, value: Number(line.price) },
        { time: lastTime, value: Number(line.price) },
      ]);
      overlays.push(overlay);
    });
    if (toNumber(summary?.current_price) !== null) {
      series.createPriceLine({
        price: Number(summary.current_price),
        color: "rgba(255,255,255,0.7)",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "Spot",
      });
    }
    return () => chart.remove();
  }, [data, summary]);

  return (
    <Panel
      title={`${ticker} K-Line`}
      eyebrow="Professional Financial Terminal-style chart"
      help="Displays the candlestick chart for the selected ticker together with spot price, target price, and valuation range overlays."
    >
      <div className="chart-host" ref={hostRef} />
      <div className="button-row chart-legend">
        <span className="legend-chip">Dashed Spot</span>
        <span className="legend-chip accent">Dashed Target</span>
        <span className="legend-chip danger">Dashed Range Low</span>
        <span className="legend-chip success">Dashed Range High</span>
      </div>
    </Panel>
  );
}

function PipelineStatus({ logs, running }) {
  const statusMap = useMemo(() => {
    const map = Object.fromEntries(PIPELINE.map((agent) => [agent, "pending"]));
    const completed = new Set(logs.map((log) => log.agent));
    PIPELINE.forEach((agent) => {
      if (completed.has(agent)) map[agent] = "done";
    });
    const last = logs.at(-1)?.agent;
    if (running && PIPELINE.includes(last)) map[last] = "running";
    if (running && !last) map.Planner = "running";
    return map;
  }, [logs, running]);

  return (
    <Panel title="Agent Pipeline" eyebrow="Planner -> Data Agent -> Valuator -> Critic -> Revisor -> Reporter">
      <div className="pipeline-grid">
        {PIPELINE.map((agent) => (
          <div key={agent} className={`pipeline-node ${statusMap[agent]}`}>
            <span className="pipeline-dot" />
            <div>
              <strong>{agent}</strong>
              <span>{statusMap[agent] === "done" ? "Completed" : statusMap[agent] === "running" ? "Running" : "Pending"}</span>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function HeroSummary({ report, validation, activeTicker }) {
  const summary = report?.report_agent?.summary || {};
  const critique = report?.structured_output?.["Critique Comments"];

  return (
    <section className="hero-shell">
      <div className="hero-copy">
        <span className="hero-pill">AI VALUATION TERMINAL | AUDIT-GRADE DCF</span>
        <h1>Institutional valuation workflow with visible agent reasoning, traceable evidence, and full DCF mechanics.</h1>
        <p>
          {activeTicker
            ? critique || `Saved valuation report loaded for ${activeTicker}.`
            : "Enter a ticker and run the workflow to generate a new report, peer screen, valuation memo, and validation trace."}
        </p>
      </div>
      <div className="hero-metrics">
        <div className="metric-card">
          <span className="metric-label">Target Price</span>
          <strong>{summary.target_price ? formatPlainCurrency(summary.target_price) : "N/A"}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Current Price</span>
          <strong>{summary.current_price ? formatPlainCurrency(summary.current_price) : "N/A"}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Valuation Range</span>
          <strong>
            {summary.valuation_range
              ? `${formatPlainCurrency(summary.valuation_range.low)} - ${formatPlainCurrency(summary.valuation_range.high)}`
              : "N/A"}
          </strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Confidence</span>
          <strong>{validation?.confidence_score ? `${validation.confidence_score}/10` : "N/A"}</strong>
        </div>
      </div>
    </section>
  );
}

function DataAvailabilityPanel({ report }) {
  const availability = report?.data_availability || {};
  const modules = safeArray(availability.modules);

  return (
    <Panel title="Data Availability" eyebrow="Primary API first, fallback only when upstream requests time out">
      {!modules.length ? (
        <EmptyState
          title="Collection status will appear here"
          body="Run the workflow to see which modules came from live APIs, which used fallback, and which timed out."
        />
      ) : (
        <>
          <div className="card-grid card-grid-3">
            {modules.map((item) => (
              <article key={item.module} className="mini-card">
                <span className="metric-label">{item.module}</span>
                <strong className={`status-pill ${String(item.status).toLowerCase().replace(/\s+/g, "-")}`}>{item.status}</strong>
                <p>{item.note}</p>
              </article>
            ))}
          </div>
          {safeArray(availability.errors).length ? (
            <div className="callout compact">
              <strong>Collector Notes:</strong> {safeArray(availability.errors).join(" | ")}
            </div>
          ) : null}
        </>
      )}
    </Panel>
  );
}

function ReportAgentPanel({ report, activeTicker }) {
  if (!report) {
    return (
      <Panel title="Report Agent" eyebrow="Phase C structured memo">
        <EmptyState
          title="No report loaded yet"
          body="The structured memo appears here after you run the valuation pipeline for a selected ticker."
        />
      </Panel>
    );
  }

  const reportAgent = report.report_agent || {};
  const companyInfo = report.company_info || {};
  const summary = reportAgent.summary || {};
  const assumptions = reportAgent.core_assumptions || {};
  const methods = reportAgent.methods || {};
  const riskFactors = safeArray(report.risk_factors);

  return (
    <Panel
      title="Report Agent"
      eyebrow="Phase C structured memo"
      actions={
        <div className="button-row">
          <a className="button button-ghost" href={`${API_BASE}/api/download/${activeTicker}/json`}>Download JSON</a>
          <a className="button button-ghost" href={`${API_BASE}/api/download/${activeTicker}/markdown`}>Download Markdown</a>
        </div>
      }
    >
      <div className="report-grid">
        <div className="feature-card">
          <span className="metric-label">Company</span>
          <strong>{companyInfo.name || activeTicker}</strong>
          <p>{companyInfo.sector || "N/A"} / {companyInfo.industry || "N/A"}</p>
        </div>
        <div className="feature-card">
          <span className="metric-label">Valuation Method</span>
          <strong>DCF + Comparable Multiples + Analyst Narrative</strong>
          <p>Deterministic code handles calculations. LLMs are limited to critique and chat explanation.</p>
        </div>
        <div className="feature-card">
          <span className="metric-label">Target Price / Range</span>
          <strong>{summary.target_price ? formatPlainCurrency(summary.target_price) : "N/A"}</strong>
          <p>
            {summary.valuation_range
              ? `${formatPlainCurrency(summary.valuation_range.low)} to ${formatPlainCurrency(summary.valuation_range.high)}`
              : "Range unavailable"}
          </p>
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-card">
          <h3>Core Assumptions</h3>
          <div className="kv-list">
            <div><span>WACC</span><strong>{formatPercent(assumptions.wacc, 3)}</strong></div>
            <div><span>Risk-Free Rate</span><strong>{formatPercent(assumptions.risk_free_rate, 2)}</strong></div>
            <div><span>Equity Risk Premium</span><strong>{formatPercent(assumptions.equity_risk_premium, 2)}</strong></div>
            <div><span>Terminal Growth</span><strong>{formatPercent(assumptions.terminal_growth_rate, 2)}</strong></div>
            <div><span>Exit Multiple</span><strong>{formatMultiple(assumptions.exit_multiple)}</strong></div>
            <div><span>Forecast Years</span><strong>{assumptions.forecast_years || "N/A"}</strong></div>
          </div>
        </div>
        <div className="detail-card">
          <h3>Method Outputs</h3>
          <div className="kv-list">
            <div><span>DCF Fair Price</span><strong>{formatPlainCurrency(methods.dcf?.fair_price)}</strong></div>
            <div><span>Comparable Fair Price</span><strong>{formatPlainCurrency(methods.comparable_multiples?.fair_price)}</strong></div>
            <div><span>Peer Count</span><strong>{methods.comparable_multiples?.peer_count || "N/A"}</strong></div>
            <div><span>Upside / Downside</span><strong>{formatPercent((summary.upside_downside_pct || 0) / 100, 1)}</strong></div>
          </div>
        </div>
        <div className="detail-card">
          <h3>Risk Factors</h3>
          <ul className="list-block">
            {riskFactors.length ? riskFactors.map((item, index) => <li key={index}>{item}</li>) : <li>No explicit risk flags recorded.</li>}
          </ul>
        </div>
      </div>
    </Panel>
  );
}

function FinancialDataPanel({ report }) {
  const financialData = safeArray(report?.financial_data);

  return (
    <Panel title="Financial Data" eyebrow="Three-statement anchors and source tags">
      {!financialData.length ? (
        <EmptyState title="Financial cards will appear here" body="Run the pipeline to populate core three-statement metrics and source links." />
      ) : (
        <div className="card-grid card-grid-4">
          {financialData.map((item) => (
            <article key={item.label} className="mini-card">
              <span className="metric-label">{item.label}</span>
              <strong>{item.unit === "ratio" ? formatPercent(item.value) : formatCurrency(item.value)}</strong>
              <a href={item.source?.citation} target="_blank" rel="noreferrer">{item.source?.provider || "Source"}</a>
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

function PeerPanel({ report }) {
  const peerGroup = report?.peer_group_analysis || {};
  const comparable = report?.comparable_analysis || {};
  const marketSnapshot = report?.market_snapshot || {};
  const target = comparable?.target_metrics || {
    ticker: marketSnapshot?.ticker || report?.company_info?.ticker,
    name: marketSnapshot?.company_name || report?.company_info?.name,
    market_cap_billions: marketSnapshot?.market_cap_billions,
    pe: marketSnapshot?.pe_trailing,
    ev_ebitda: marketSnapshot?.ev_ebitda,
    pb: marketSnapshot?.price_to_book,
    ev_revenue: marketSnapshot?.ev_revenue,
    roe: marketSnapshot?.roe,
    match_tier: "Current Company",
    match_score: 100,
  };
  const peers = [target, ...safeArray(peerGroup.selected_peers)].filter(Boolean);
  const comparison = comparable?.comparison_vs_peer_stats || {};
  const statRows = [
    ["P/E", target?.pe, comparable?.peer_statistics?.median_pe, comparison?.pe_vs_median_pct, "Median peer P/E"],
    ["EV/EBITDA", target?.ev_ebitda, comparable?.peer_statistics?.median_ev_ebitda, comparison?.ev_ebitda_vs_median_pct, "Median peer EV/EBITDA"],
    ["P/B", target?.pb, comparable?.peer_statistics?.mean_pb, comparison?.pb_vs_peer_mean_pct, "Mean peer P/B"],
    ["EV/Sales", target?.ev_revenue, comparable?.peer_statistics?.mean_ev_sales, comparison?.ev_sales_vs_peer_mean_pct, "Mean peer EV/Sales"],
    ["ROE", target?.roe, comparable?.peer_statistics?.mean_roe, comparison?.roe_vs_peer_mean_pct, "Mean peer ROE"],
  ];
  const logPreview = safeArray(peerGroup.selection_log);

  return (
    <Panel title="Peer Group Analysis" eyebrow="Three-tier comparable company selection">
      <div className="callout">
        {peerGroup.warning || "Final output targets at least 6 peers. Tier logic and rejection reasons are logged for auditability."}
      </div>
      <div className="rule-chip-row">
        {safeArray(peerGroup.rules).map((rule, index) => (
          <span className="rule-chip" key={index}>{rule}</span>
        ))}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Name</th>
              <th>Tier</th>
              <th>Market Cap (USD bn)</th>
              <th>P/E</th>
              <th>EV/EBITDA</th>
              <th>P/B</th>
              <th>EV/Sales</th>
              <th>ROE</th>
            </tr>
          </thead>
          <tbody>
            {peers.map((peer) => (
              <tr key={peer.ticker} className={peer.match_tier === "Current Company" ? "target-row" : ""}>
                <td>{peer.ticker}</td>
                <td>{peer.name}</td>
                <td>{peer.match_tier}</td>
                <td>{formatNumber(peer.market_cap_billions)}</td>
                <td>{formatNumber(peer.pe)}</td>
                <td>{formatNumber(peer.ev_ebitda)}</td>
                <td>{formatNumber(peer.pb)}</td>
                <td>{formatNumber(peer.ev_revenue)}</td>
                <td>{formatPercent(peer.roe, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="detail-grid">
        <div className="detail-card">
          <h3>Peer Statistics vs Current Company</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Current Company</th>
                  <th>Peer Anchor</th>
                  <th>Delta</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {statRows.map(([label, targetValue, anchorValue, delta, note]) => (
                  <tr key={label}>
                    <td>{label}</td>
                    <td className="mono">{label === "ROE" ? formatPercent(targetValue, 2) : formatNumber(targetValue)}</td>
                    <td className="mono">{label === "ROE" ? formatPercent(anchorValue, 2) : formatNumber(anchorValue)}</td>
                    <td className="mono">{formatDeltaPercent(delta)}</td>
                    <td>{note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="detail-card detail-card-wide">
          <h3>Selection Trace Preview</h3>
          <div className="trace-list trace-list-scroll">
            {logPreview.length ? logPreview.map((item, index) => (
              <div key={`${item.ticker}-${index}`} className="trace-row">
                <strong>{item.ticker || "Candidate"}</strong>
                <span>{item.tier || "Review"}</span>
                <p>{item.reason || "No reason recorded."}</p>
              </div>
            )) : <p className="muted-copy">Selection trace appears here after peer screening completes.</p>}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function ContextPanel({ report }) {
  const companyInfo = report?.company_info || {};
  const context = report?.contextual_data || {};
  const news = safeArray(context.recent_news).slice(0, 10);
  const filingExcerpts = safeArray(context.filing_excerpts).slice(0, 10);
  const callExcerpts = safeArray(context.call_excerpts).slice(0, 10);

  return (
    <Panel title="Contextual Evidence" eyebrow="Business description, recent news, filing excerpts, and retrieval context">
      <div className="detail-grid context-grid">
        <div className="detail-card context-section">
          <h3>Business Description</h3>
          <div className="scroll-block">
            <p>{context.business_description?.description || companyInfo.summary || "Business description not yet populated."}</p>
          </div>
          <div className="context-footer">
            {context.business_description?.source_url ? (
              <a href={context.business_description.source_url} target="_blank" rel="noreferrer">
                Source: {sourceHost(context.business_description.source_url)}
              </a>
            ) : null}
          </div>
        </div>
        <div className="detail-card context-section">
          <h3>Filing / Call Excerpts</h3>
          <div className="scroll-block stack-list">
            {callExcerpts.length ? callExcerpts.map((item, index) => {
              const source = item.source || {};
              return (
                <div className="quote-card" key={`call-${index}`}>
                  <p>{item.excerpt || "No excerpt text available."}</p>
                  {source.citation ? (
                    <a href={source.citation} target="_blank" rel="noreferrer">
                      {source.provider || "Source"}
                    </a>
                  ) : (
                    <span className="muted-copy">{source.provider || "Source unavailable"}</span>
                  )}
                </div>
              );
            }) : <p className="muted-copy">Call and filing excerpts will appear here when the collection layer finds them.</p>}
          </div>
        </div>
        <div className="detail-card context-section">
          <h3>Recent Filings</h3>
          <div className="scroll-block stack-list">
            {filingExcerpts.length ? filingExcerpts.map((item, index) => (
              <div className="quote-card" key={`filing-${index}`}>
                <strong>{item.type || "Filing"}</strong>
                <p>{item.title || "Untitled filing"}</p>
                <span className="muted-copy">{item.date || "Date unavailable"}</span>
                <div className="button-row">
                  {item.edgar_url ? <a className="button button-ghost chipish" href={item.edgar_url} target="_blank" rel="noreferrer">EDGAR</a> : null}
                  {item.primary_doc_url ? <a className="button button-ghost chipish" href={item.primary_doc_url} target="_blank" rel="noreferrer">Primary Doc</a> : null}
                  {item.press_release_url ? <a className="button button-ghost chipish" href={item.press_release_url} target="_blank" rel="noreferrer">Press Release</a> : null}
                  {item.excel_url ? <a className="button button-ghost chipish" href={item.excel_url} target="_blank" rel="noreferrer">Excel</a> : null}
                </div>
              </div>
            )) : <p className="muted-copy">Recent filings will appear here when the collection layer finds them.</p>}
          </div>
        </div>
        <div className="detail-card context-section context-news-panel">
          <h3>News</h3>
          <div className="scroll-block stack-list">
            {news.length ? news.map((item, index) => (
              <a key={index} className="news-row-card" href={item.url || item.link || "#"} target="_blank" rel="noreferrer">
                <div className="news-row-header">
                  <span>{item.publisher || "News"}</span>
                  <time>{item.published_at || item.date || "Recent"}</time>
                </div>
                <strong>{item.title || "Untitled headline"}</strong>
                <p>{item.summary || "Click through for the full article."}</p>
              </a>
            )) : <p className="muted-copy">Recent news is currently sparse for this saved report. The UI remains ready to display retrieved headlines when available.</p>}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function DcfFlowMap({ report, activeStage, onStageSelect }) {
  if (!report) {
    return <EmptyState title="DCF flow map unavailable" body="Run the valuation workflow to render the valuation route map." />;
  }

  const keyInputs = report?.structured_output?.["Key Inputs"] || {};
  const assumptions = report?.report_agent?.core_assumptions || {};
  const wacc = report?.calculation_details?.wacc_details || {};
  const terminal = report?.calculation_details?.terminal_value || {};
  const bridge = report?.calculation_details?.valuation_bridge || {};
  const validation = report?.validation_agents || {};
  const summary = report?.report_agent?.summary || {};

  const columns = [
    {
      key: "input",
      title: "Input Gate",
      subtitle: "What enters the model",
      agents: "Planner / DataCollector",
      targetId: "dcf-module-wacc",
      items: [
        { label: "Revenue (LTM)", value: formatCurrency(keyInputs.revenue), note: "Three-statement base" },
        { label: "EBIT (LTM)", value: formatCurrency(keyInputs.ebit), note: "Operating earnings anchor" },
        { label: "Net Debt", value: formatCurrency(keyInputs.net_debt), note: "Capital structure bridge" },
        { label: "Risk-Free Rate", value: formatPercent(assumptions.risk_free_rate, 2), note: "FRED" },
        { label: "Beta", value: formatNumber(wacc.beta, 3), note: wacc.assumption_audit?.beta?.source || "Market beta" },
        { label: "Terminal Growth", value: formatPercent(assumptions.terminal_growth_rate, 2), note: terminal.assumption_audit?.terminal_growth?.source || "Macro anchor" },
      ],
    },
    {
      key: "calculation",
      title: "Calculation Gate",
      subtitle: "How inputs become valuation",
      agents: "Valuator",
      targetId: "dcf-module-forecast",
      items: [
        { label: "Cost of Equity", value: formatPercent(wacc.cost_of_equity, 3), note: "Rf + Beta x ERP" },
        { label: "Final WACC", value: formatPercent(wacc.wacc, 3), note: "(E/V) x Re + (D/V) x Rd x (1-Tc)" },
        { label: "PV of Explicit UFCF", value: formatCurrency(bridge.pv_explicit_fcf), note: "5-year forecast discounted" },
        { label: "PV of Terminal Value", value: formatCurrency(bridge.pv_terminal_value), note: "Gordon + exit multiple cross-check" },
        { label: "Enterprise Value", value: formatCurrency(bridge.enterprise_value), note: "Operating asset value" },
        { label: "Equity Value", value: formatCurrency(bridge.equity_value), note: "EV - Net Debt" },
      ],
    },
    {
      key: "decision",
      title: "Decision Gate",
      subtitle: "What the critic checks",
      agents: "Critic / Revisor",
      targetId: "validation-panel-anchor",
      items: [
        { label: "Rules Passed", value: `${safeArray(validation.rule_results).filter((item) => item.passed).length}/${safeArray(validation.rule_results).length || 0}`, note: "Rule engine" },
        { label: "Confidence", value: validation.confidence_score ? `${validation.confidence_score}/10` : "N/A", note: validation.confidence_label || "Confidence label" },
        { label: "Peer Depth", value: `${report?.comparable_analysis?.peer_count || 0} peers`, note: "Comparable screen coverage" },
        { label: "Terminal Value Weight", value: safeArray(validation.rule_results).find((item) => item.rule?.includes("Terminal value"))?.detail || "N/A", note: "Long-duration dependence" },
        { label: "Evidence Audit", value: `${safeArray(validation.evidence_mapping).length} mappings`, note: "Assumption-to-evidence links" },
        { label: "Revision Loop", value: `${safeArray(validation.uncertainty_agent?.findings).length} key flags`, note: "Critic -> Revisor visibility" },
      ],
    },
    {
      key: "result",
      title: "Result Gate",
      subtitle: "How all roads converge",
      agents: "Reporter",
      targetId: "report-agent-anchor",
      items: [
        { label: "DCF Fair Price", value: formatPlainCurrency(bridge.fair_price_per_share), note: "Intrinsic value per share" },
        { label: "Target Price", value: formatPlainCurrency(summary.target_price), note: "Report output" },
        { label: "Valuation Range", value: summary.valuation_range ? `${formatPlainCurrency(summary.valuation_range.low)} to ${formatPlainCurrency(summary.valuation_range.high)}` : "N/A", note: "Bull / bear envelope" },
        { label: "Current Price", value: formatPlainCurrency(summary.current_price), note: "Market reference" },
        { label: "Upside / Downside", value: formatPercent((summary.upside_downside_pct || 0) / 100, 1), note: "Target vs market" },
        { label: "Final Memo", value: "JSON + Markdown", note: "Downloadable report pack" },
      ],
    },
  ];

  return (
    <div className="module-card flow-map-card">
      <div className="module-heading">
        <h3>0. DCF Flow Map</h3>
        <p>A DuPont-style aggregation view that shows how evidence and deterministic calculations converge into one intrinsic value output.</p>
      </div>
      <div className="flow-map-grid">
        {columns.map((column, index) => (
          <button
            type="button"
            className={`flow-stage ${activeStage === column.key ? "active" : ""}`}
            key={column.title}
            onClick={() => onStageSelect?.(column.targetId)}
          >
            <div className="flow-stage-head">
              <span className="metric-label">Stage {index + 1}</span>
              <h4>{column.title}</h4>
              <p>{column.subtitle}</p>
              <span className="flow-agent-link">{column.agents}</span>
            </div>
            <div className="flow-stage-list">
              {column.items.map((item) => (
                <div className="flow-node" key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <p>{item.note}</p>
                </div>
              ))}
            </div>
          </button>
        ))}
      </div>
      <div className="flow-map-footer">
        <div className="flow-convergence">
          <span className="metric-label">One Line Conclusion</span>
          <strong>
            {formatPlainCurrency(summary.target_price)} target price derived from traceable inputs, deterministic DCF math, critic checks, and report synthesis.
          </strong>
        </div>
      </div>
    </div>
  );
}

function WaccModule({ details }) {
  if (!details || !Object.keys(details).length) {
    return <EmptyState title="WACC breakdown unavailable" body="Run an analysis to populate the capital cost assumptions." />;
  }

  const rows = [
    ["Risk-Free Rate (Rf)", "Latest 10Y Treasury yield anchor", formatPercent(details.risk_free_rate, 2), "FRED DGS10"],
    ["Beta", "24M equity beta", formatNumber(details.beta, 3), details.assumption_audit?.beta?.source || "Yahoo Finance"],
    ["Equity Risk Premium", "Market ERP assumption", formatPercent(details.equity_risk_premium, 2), "Damodaran / FRED"],
    [
      "Cost of Equity (Ke)",
      "Ke = Rf + Beta x ERP",
      `${formatPercent(details.risk_free_rate, 2)} + ${formatNumber(details.beta, 3)} x ${formatPercent(details.equity_risk_premium, 2)} = ${formatPercent(details.cost_of_equity, 3)}`,
      "Deterministic code",
    ],
    ["Cost of Debt (Kd)", "Interest expense / debt", formatPercent(details.cost_of_debt, 2), details.assumption_audit?.cost_of_debt?.source || "Financial statements"],
    ["Effective Tax Rate (Tc)", "Income tax / pretax income", formatPercent(details.effective_tax_rate, 2), "Historical company tax rate"],
    ["Equity Weight (E/V)", "Market cap / (market cap + net debt)", formatPercent(details.equity_weight, 2), details.assumption_audit?.capital_structure?.source || "Capital structure"],
    ["Debt Weight (D/V)", "Net debt / (market cap + net debt)", formatPercent(details.debt_weight, 2), details.assumption_audit?.capital_structure?.source || "Capital structure"],
    ["Final WACC", "WACC = (E/V) x Ke + (D/V) x Kd x (1-Tc)", formatPercent(details.wacc, 3), "Deterministic code"],
  ];

  return (
    <div className="module-card" id="dcf-module-wacc">
      <div className="module-heading">
        <h3>1. WACC Complete Breakdown</h3>
        <p>{details.formula}</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Formula</th>
              <th>Value</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([item, formula, value, source]) => (
              <tr key={item}>
                <td>{item}</td>
                <td>{formula}</td>
                <td className="mono">{value}</td>
                <td>{source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ForecastModule({ details, report }) {
  const rows = safeArray(details?.forecast_table);
  const ltm = report?.structured_output?.["Key Inputs"] || {};

  return (
    <div className="module-card" id="dcf-module-forecast">
      <div className="module-heading">
        <h3>2. 5-Year UFCF Forecast</h3>
        <p>Each line item shows the deterministic bridge from revenue assumptions to unlevered free cash flow.</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Forecast Item</th>
              <th>LTM</th>
              {rows.map((row) => <th key={row.year}>Year {row.year}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Revenue</td>
              <td className="mono">{formatCurrency(ltm.revenue)}</td>
              {rows.map((row) => <td className="mono" key={`rev-${row.year}`}>{formatCurrency(row.revenue)}</td>)}
            </tr>
            <tr>
              <td>Revenue Growth</td>
              <td className="mono">-</td>
              {rows.map((row) => <td className="mono" key={`growth-${row.year}`}>{formatPercent(row.growth, 2)}</td>)}
            </tr>
            <tr>
              <td>EBIT</td>
              <td className="mono">{formatCurrency(ltm.ebit)}</td>
              {rows.map((row) => <td className="mono" key={`ebit-${row.year}`}>{formatCurrency(row.ebit)}</td>)}
            </tr>
            <tr>
              <td>NOPAT</td>
              <td className="mono">{formatCurrency(ltm.ebit && ltm.effective_tax_rate !== undefined ? ltm.ebit * (1 - ltm.effective_tax_rate) : null)}</td>
              {rows.map((row) => <td className="mono" key={`nopat-${row.year}`}>{formatCurrency(row.nopat)}</td>)}
            </tr>
            <tr>
              <td>D&A</td>
              <td className="mono">{formatCurrency(ltm.depreciation_and_amortization)}</td>
              {rows.map((row) => <td className="mono" key={`da-${row.year}`}>{formatCurrency(row.da)}</td>)}
            </tr>
            <tr>
              <td>Delta Working Capital</td>
              <td className="mono">N/A</td>
              {rows.map((row) => <td className="mono" key={`wc-${row.year}`}>{formatCurrency(row.delta_wc)}</td>)}
            </tr>
            <tr>
              <td>CapEx</td>
              <td className="mono">{formatCurrency(ltm.capex)}</td>
              {rows.map((row) => <td className="mono" key={`capex-${row.year}`}>{formatCurrency(row.capex)}</td>)}
            </tr>
            <tr>
              <td>UFCF</td>
              <td className="mono">{formatCurrency(ltm.unlevered_free_cash_flow)}</td>
              {rows.map((row) => <td className="mono" key={`ufcf-${row.year}`}>{formatCurrency(row.ufcf)}</td>)}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TerminalValueModule({ details }) {
  if (!details || !Object.keys(details).length) {
    return <EmptyState title="Terminal value unavailable" body="The composite terminal value output appears after the DCF run." />;
  }

  return (
    <div className="module-card" id="dcf-module-terminal">
      <div className="module-heading">
        <h3>3. Terminal Value Cross-Check</h3>
        <p>Gordon Growth and exit multiple are shown side by side so the interviewer can audit both anchors.</p>
      </div>
      <div className="detail-grid">
        <div className="detail-card">
          <span className="metric-label">Gordon Growth Method</span>
          <strong>{formatCurrency(details.tv_gordon)}</strong>
          <p className="formula-line">TV = Terminal UFCF x (1 + g) / (WACC - g)</p>
          <p className="formula-line">
            g = {formatPercent(details.terminal_growth, 2)} from {details.assumption_audit?.terminal_growth?.source || "macro anchor"}
          </p>
        </div>
        <div className="detail-card">
          <span className="metric-label">Exit Multiple Method</span>
          <strong>{formatCurrency(details.tv_exit_multiple)}</strong>
          <p className="formula-line">TV = Terminal EBITDA x peer median EV/EBITDA</p>
          <p className="formula-line">
            Exit Multiple = {formatMultiple(details.exit_multiple_used)} from {details.assumption_audit?.exit_multiple?.source || "peer set"}
          </p>
        </div>
        <div className="detail-card">
          <span className="metric-label">Composite Terminal Value</span>
          <strong>{formatCurrency(details.tv_composite)}</strong>
          <p className="formula-line">Composite TV = weighted blend of Gordon Growth and exit multiple outputs</p>
        </div>
      </div>
    </div>
  );
}

function BridgeModule({ details }) {
  if (!details || !Object.keys(details).length) {
    return <EmptyState title="Valuation bridge unavailable" body="Enterprise value and equity bridge will appear after the DCF run." />;
  }

  return (
    <div className="module-card" id="dcf-module-bridge">
      <div className="module-heading">
        <h3>4. Enterprise Value to Equity Value Bridge</h3>
        <p>The bridge makes the conversion from discounted operating assets to per-share equity value explicit.</p>
      </div>
      <div className="formula-stack">
        <div className="formula-card">
          <span>Enterprise Value</span>
          <strong>{formatCurrency(details.enterprise_value)}</strong>
          <p>EV = PV of explicit UFCF + PV of terminal value = {formatCurrency(details.pv_explicit_fcf)} + {formatCurrency(details.pv_terminal_value)}</p>
        </div>
        <div className="formula-card">
          <span>Equity Value</span>
          <strong>{formatCurrency(details.equity_value)}</strong>
          <p>Equity Value = EV - Net Debt = {formatCurrency(details.enterprise_value)} - {formatCurrency(details.net_debt)}</p>
        </div>
        <div className="formula-card">
          <span>Fair Value Per Share</span>
          <strong>{formatPlainCurrency(details.fair_price_per_share)}</strong>
          <p>Fair Price = Equity Value / Shares Outstanding = {formatCurrency(details.equity_value)} / {formatNumber(details.shares_outstanding, 0)}</p>
        </div>
      </div>
    </div>
  );
}

function ScenarioModule({ scenarios }) {
  const entries = Object.entries(scenarios || {});
  return (
    <div className="module-card">
      <div className="module-heading">
        <h3>5. Scenario Analysis</h3>
        <p>Base, bull, and bear cases communicate how core assumptions reshape the intrinsic value range.</p>
      </div>
      <div className="card-grid card-grid-3">
        {entries.map(([name, item]) => (
          <div className="mini-card" key={name}>
            <span className="metric-label">{name}</span>
            <strong>{formatPlainCurrency(item?.fair_price)}</strong>
            <p>{item?.description || "No description available."}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function SensitivityModule({ matrix }) {
  const grid = matrix?.sensitivity_matrix || {};
  const growthRates = Object.keys(grid);
  const waccRates = growthRates.length ? Object.keys(grid[growthRates[0]] || {}) : [];

  return (
    <div className="module-card">
      <div className="module-heading">
        <h3>6. Sensitivity Matrix</h3>
        <p>{matrix?.note || "Per-share valuation sensitivity across WACC and terminal growth assumptions."}</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Terminal Growth \\ WACC</th>
              {waccRates.map((rate) => <th key={rate}>{rate}</th>)}
            </tr>
          </thead>
          <tbody>
            {growthRates.map((growth) => (
              <tr key={growth}>
                <td>{growth}</td>
                {waccRates.map((rate) => {
                  const isBase = rate === matrix?.base_wacc && growth === matrix?.base_terminal_growth;
                  return (
                    <td key={`${growth}-${rate}`} className={isBase ? "cell-highlight mono" : "mono"}>
                      {formatPlainCurrency(grid[growth]?.[rate])}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DcfPanel({ report, activeStage, onStageSelect }) {
  const details = report?.calculation_details || {};

  return (
    <Panel title="DCF Calculation Modules" eyebrow="Six-step deterministic model walkthrough with formula display">
      {!report ? (
        <EmptyState title="DCF modules will appear here" body="Once the valuation run finishes, each step will render as formulas, tables, and valuation bridges instead of raw JSON." />
      ) : (
        <div className="module-stack">
          <DcfFlowMap report={report} activeStage={activeStage} onStageSelect={onStageSelect} />
          <WaccModule details={details.wacc_details} />
          <ForecastModule details={details} report={report} />
          <TerminalValueModule details={details.terminal_value} />
          <BridgeModule details={details.valuation_bridge} />
          <ScenarioModule scenarios={report.scenario_analysis} />
          <SensitivityModule matrix={details.sensitivity_matrix} />
        </div>
      )}
    </Panel>
  );
}

function ValidationPanel({ report }) {
  const validation = report?.validation_agents || {};

  return (
    <div id="validation-panel-anchor">
    <Panel title="Validation & Critic Mechanisms" eyebrow="Inconsistency checks, evidence mapping, and confidence scoring">
      {!report ? (
        <EmptyState title="Validation results will appear here" body="The critic and self-correction output is shown after the pipeline completes." />
      ) : (
        <div className="detail-grid">
        <div className="detail-card">
          <h3>Inconsistency Detection</h3>
          <div className="stack-list scroll-block">
            {safeArray(validation.rule_results).map((item, index) => (
              <div key={index} className={`rule-result ${item.passed ? "pass" : "fail"}`}>
                <strong>{item.rule}</strong>
                  <p>{item.detail}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="detail-card">
            <h3>Evidence Audit</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Assumption</th>
                    <th>Supporting Evidence</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {safeArray(validation.evidence_mapping).map((item, index) => (
                    <tr key={index}>
                      <td>{item.assumption}</td>
                      <td>{item.supporting_evidence}</td>
                      <td>
                        <a href={item.source} target="_blank" rel="noreferrer">{sourceHost(item.source)}</a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
        </div>
        <div className="detail-card">
          <h3>Uncertainty & Confidence</h3>
          <div className="scroll-block stack-list">
            <div className="kv-list">
              {safeArray(validation.confidence_breakdown).map((item, index) => (
                <div key={index}>
                  <span>{item.item}</span>
                  <strong>{item.delta ? `${item.delta}` : item.remaining}</strong>
                </div>
              ))}
            </div>
            <div className="callout compact">
              <strong>Critic Summary:</strong> {validation.critic_summary || "No critic summary available."}
            </div>
            {safeArray(validation.uncertainty_agent?.findings).length ? (
              <div className="callout compact">
                <strong>Uncertainty Flags:</strong> {safeArray(validation.uncertainty_agent?.findings).join(" | ")}
              </div>
            ) : null}
          </div>
        </div>
      </div>
      )}
    </Panel>
    </div>
  );
}

function PipelineTracePanel({ logs }) {
  return (
    <Panel title="Pipeline Trace" eyebrow="Timestamped execution log and visible agent state">
      {!logs.length ? (
        <EmptyState title="No trace yet" body="Execution events will stream here in real time when you run a valuation workflow." />
      ) : (
        <div className="trace-list trace-list-scroll">
          {logs.map((log, index) => (
            <div className="trace-row" key={`${log.agent}-${index}`}>
              <strong>{log.timestamp || ""} {log.agent}</strong>
              <p>{log.message}</p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function EvidencePanel({ report }) {
  return (
    <Panel title="Evidence Sources" eyebrow="Every visible output should remain source-traceable">
      {!report?.citations?.length ? (
        <EmptyState title="Source links will appear here" body="Market, financial, macro, and narrative citations are listed after report generation." />
      ) : (
        <div className="source-grid">
          {report.citations.map((citation, index) => (
            <a key={index} className="source-card" href={citation.url} target="_blank" rel="noreferrer">
              <span>{citation.label}</span>
              <strong>{sourceHost(citation.url)}</strong>
            </a>
          ))}
        </div>
      )}
    </Panel>
  );
}

function FloatingChat({ open, onToggle, ticker, apiConfig, report }) {
  const [question, setQuestion] = useState("Please explain the DCF assumptions and cite the evidence.");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function askQuestion() {
    if (!ticker || !question.trim() || !apiConfig.api_key) return;
    const prompt = question.trim();
    setLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: prompt }]);
    try {
      const response = await fetch(`${API_BASE}/api/chat/${ticker}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: prompt,
          api_key: apiConfig.api_key,
          base_url: apiConfig.base_url,
          model: apiConfig.model || "gemini-flash-latest",
        }),
      });
      const payload = await response.json();
      setMessages((prev) => [...prev, { role: "assistant", ...payload }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: "assistant", answer: `Chat failed: ${error.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button className={`chat-fab ${open ? "active" : ""}`} onClick={onToggle}>
        {open ? "Close Chat" : "Open Chat"}
      </button>
      <div className={`chat-drawer ${open ? "open" : ""}`}>
        <div className="chat-header">
          <div>
            <p className="panel-eyebrow">Conversational RAG Agent</p>
            <h3>Report Explainer</h3>
          </div>
          <button className="button button-ghost" onClick={onToggle}>Close</button>
        </div>
        <div className="chat-callout">
          <strong>Loaded context:</strong> report summary, peer analysis, WACC, forecast table, terminal value, valuation bridge, validation findings, filings, news, and risk factors.
        </div>
        {!apiConfig.api_key ? (
          <div className="callout">
            Please open API Settings and provide your own API key to enable Gemini or another supported model.
          </div>
        ) : null}
        {!report ? (
          <EmptyState title="No report in memory" body="Run the valuation workflow first so the chat agent has a report to retrieve from." />
        ) : (
          <>
            <div className="chat-thread">
              {messages.length ? messages.map((message, index) => (
                <div key={index} className={`chat-bubble ${message.role}`}>
                  <p>{message.content || message.answer}</p>
                  {message.retrieved_sections?.length ? (
                    <div className="chat-meta">Sections: {message.retrieved_sections.join(", ")}</div>
                  ) : null}
                  {message.citations?.length ? (
                    <div className="button-row">
                      {message.citations.map((citation, citeIndex) => (
                        <a key={`${citation.url}-${citeIndex}`} className="button button-ghost chipish" href={citation.url} target="_blank" rel="noreferrer">
                          {citation.label || sourceHost(citation.url)}
                        </a>
                      ))}
                    </div>
                  ) : null}
                </div>
              )) : <p className="muted-copy">Ask about assumptions, evidence, risks, or a specific DCF step.</p>}
            </div>
            <div className="chat-compose">
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                disabled={!apiConfig.api_key}
                placeholder="Ask the report explainer to interpret a calculation and cite the supporting evidence."
              />
              <button
                className="button button-primary"
                onClick={askQuestion}
                disabled={!apiConfig.api_key || !report || loading}
              >
                {loading ? "Thinking..." : "Ask Agent"}
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default function App() {
  const [inputTicker, setInputTicker] = useState("AAPL");
  const [activeTicker, setActiveTicker] = useState("");
  const [report, setReport] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [logs, setLogs] = useState([]);
  const [running, setRunning] = useState(false);
  const [fatalError, setFatalError] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [apiConfig, setApiConfig] = useState(() => ({
    model: "gemini-flash-latest",
    base_url: "",
    ...readApiConfig(),
  }));

  useEffect(() => {
    if (!activeTicker) {
      setChartData([]);
      return;
    }

    fetch(`${API_BASE}/api/chart/${activeTicker}`)
      .then((response) => response.json())
      .then((data) => setChartData(Array.isArray(data) ? data : []))
      .catch(() => setChartData([]));
  }, [activeTicker]);

  useEffect(() => {
    if (!apiConfig.api_key) {
      setDrawerOpen(true);
    }
  }, [apiConfig.api_key]);

  function persistApiConfig(config) {
    const merged = {
      model: "gemini-flash-latest",
      base_url: "",
      ...config,
    };
    saveApiConfig(merged);
    setApiConfig(merged);
    setDrawerOpen(false);
  }

  function runAnalysis() {
    const nextTicker = inputTicker.trim().toUpperCase();
    if (!nextTicker) return;

    setActiveTicker(nextTicker);
    setReport(null);
    setLogs([]);
    setFatalError("");
    setRunning(true);

    const source = new EventSource(`${API_BASE}/api/evaluate/${nextTicker}`);
    source.addEventListener("log", (event) => {
      const payload = JSON.parse(event.data);
      setLogs((prev) => [...prev, { ...payload, timestamp: new Date().toLocaleTimeString() }]);
    });
    source.addEventListener("complete", (event) => {
      const payload = JSON.parse(event.data);
      setReport(payload.report);
      setRunning(false);
      source.close();
    });
    source.addEventListener("fatal", (event) => {
      const payload = JSON.parse(event.data);
      setLogs((prev) => [...prev, { ...payload, timestamp: new Date().toLocaleTimeString() }]);
      setFatalError(payload.message || "Invalid ticker code. Please enter a valid listed stock symbol.");
      setRunning(false);
      source.close();
    });
    source.onerror = () => {
      setFatalError((prev) => prev || "The request failed before a valid report was generated.");
      setRunning(false);
      source.close();
    };
  }

  const validation = report?.validation_agents || {};
  const activeFlowStage = running ? FLOW_STAGE_BY_AGENT[logs.at(-1)?.agent] || "input" : null;

  function scrollToAnchor(anchorId) {
    const element = document.getElementById(anchorId);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <div className="app-shell">
      <ApiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} apiConfig={apiConfig} onSave={persistApiConfig} />
      <FloatingChat open={chatOpen} onToggle={() => setChatOpen((prev) => !prev)} ticker={activeTicker} apiConfig={apiConfig} report={report} />

      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-kicker">AI Valuation Terminal</span>
          <strong>AI VALUATION TERMINAL | AUDIT-GRADE DCF</strong>
        </div>
        <div className="toolbar">
          <input
            value={inputTicker}
            onChange={(event) => setInputTicker(event.target.value.toUpperCase())}
            placeholder="Ticker"
            list="ticker-suggestions"
          />
          <datalist id="ticker-suggestions">
            {TICKER_SUGGESTIONS.map((ticker) => (
              <option key={ticker} value={ticker} />
            ))}
          </datalist>
          <button className="button button-ghost" onClick={() => setDrawerOpen(true)}>API Settings</button>
          <button className="button button-primary" onClick={runAnalysis} disabled={running}>
            {running ? "Running..." : "Run Analysis"}
          </button>
        </div>
      </header>

      <HeroSummary report={report} validation={validation} activeTicker={activeTicker} />
      {!apiConfig.api_key ? (
        <div className="callout fatal-callout">
          Add your API key in API Settings to fully enable the Conversational RAG Agent.
        </div>
      ) : null}
      {fatalError ? <div className="callout fatal-callout">{fatalError}</div> : null}
      <DataAvailabilityPanel report={report} />
      <PipelineStatus logs={logs} running={running} />

      <div className="page-grid">
        <div className="page-column">
          {activeTicker ? (
            <CandlestickPanel ticker={activeTicker} data={chartData} summary={report?.report_agent?.summary} />
          ) : (
            <Panel title="K-Line Chart" eyebrow="Professional Financial Terminal-style chart">
              <EmptyState title="No chart loaded" body="The candlestick chart loads for the active research ticker after you run an analysis." />
            </Panel>
          )}
          <div id="report-agent-anchor">
            <ReportAgentPanel report={report} activeTicker={activeTicker || inputTicker} />
          </div>
          <FinancialDataPanel report={report} />
          <PeerPanel report={report} />
          <ContextPanel report={report} />
          <DcfPanel report={report} activeStage={activeFlowStage} onStageSelect={scrollToAnchor} />
          <ValidationPanel report={report} />
          <PipelineTracePanel logs={logs} />
          <EvidencePanel report={report} />
        </div>
      </div>
    </div>
  );
}
