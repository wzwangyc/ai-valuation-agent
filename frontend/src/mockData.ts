import { 
  CompanyProfile, 
  FinancialMetric, 
  FinancialStatement, 
  DCFCalculation, 
  AgentLog, 
  ValidationIssue, 
  ValuationReport,
  NewsItem,
  RAGExcerpt
} from './types/valuation';

export const mockCompanyProfile: CompanyProfile = {
  name: "Agilent Technologies",
  ticker: "A",
  description: "Agilent Technologies, Inc. provides application-focused solutions to the life sciences, diagnostics, and applied chemical markets worldwide. It operates through Life Sciences and Applied Markets; Diagnostics and Genomics; and Agilent CrossLab segments.",
  sector: "Healthcare",
  industry: "Diagnostics & Research",
  headquarters: "Santa Clara, California",
  employees: 18100,
  website: "https://www.agilent.com",
  sources: ["Yahoo Finance", "SEC EDGAR 10-K"]
};

export const mockMetrics: FinancialMetric[] = [
  { label: "Current Price", value: "$111.30", source: "Market Data" },
  { label: "Market Cap", value: "$32.4B", source: "Market Data" },
  { label: "EV", value: "$34.1B", source: "Calculated" },
  { label: "Trailing P/E", value: "24.5x", source: "Yahoo Finance" },
  { label: "EV/EBITDA", value: "18.2x", source: "Calculated" },
  { label: "P/B", value: "5.1x", source: "Yahoo Finance" },
  { label: "52W High", value: "$154.20", source: "Market Data" },
  { label: "52W Low", value: "$101.50", source: "Market Data" },
];

export const mockFinancials: FinancialStatement = {
  revenue: [
    { label: "Revenue", value: 6833000000, year: 2023, source: "SEC 10-K" },
    { label: "Revenue", value: 6848000000, year: 2022, source: "SEC 10-K" },
    { label: "Revenue", value: 6319000000, year: 2021, source: "SEC 10-K" },
  ],
  ebit: [
    { label: "EBIT", value: 1625000000, year: 2023, source: "Calculated" },
    { label: "EBIT", value: 1650000000, year: 2022, source: "Calculated" },
    { label: "EBIT", value: 1450000000, year: 2021, source: "Calculated" },
  ],
  netIncome: [
    { label: "Net Income", value: 1240000000, year: 2023, source: "SEC 10-K" },
    { label: "Net Income", value: 1254000000, year: 2022, source: "SEC 10-K" },
    { label: "Net Income", value: 1210000000, year: 2021, source: "SEC 10-K" },
  ],
  fcf: [
    { label: "FCF", value: 1150000000, year: 2023, source: "Calculated" },
    { label: "FCF", value: 1310000000, year: 2022, source: "Calculated" },
    { label: "FCF", value: 1200000000, year: 2021, source: "Calculated" },
  ],
  cogs: [], grossProfit: [], operatingCashFlow: [], capex: [], cash: [], debt: [], equity: []
};

export const mockDCF: DCFCalculation = {
  wacc: {
    riskFreeRate: 0.042,
    beta: 1.1,
    erp: 0.055,
    costOfEquity: 0.1025,
    costOfDebt: 0.05,
    taxRate: 0.18,
    equityWeight: 0.95,
    debtWeight: 0.05,
    finalWacc: 0.1117
  },
  forecast: [
    { year: 2024, revenue: 7174000000, growth: 0.05, ebit: 1750000000, ebitMargin: 0.24, nopat: 1435000000, da: 300000000, deltaWC: -50000000, capex: -350000000, ufcf: 1335000000 },
    { year: 2025, revenue: 7533000000, growth: 0.05, ebit: 1840000000, ebitMargin: 0.24, nopat: 1508800000, da: 310000000, deltaWC: -52000000, capex: -360000000, ufcf: 1406800000 },
    { year: 2026, revenue: 7909000000, growth: 0.05, ebit: 1932000000, ebitMargin: 0.24, nopat: 1584240000, da: 320000000, deltaWC: -54000000, capex: -370000000, ufcf: 1480240000 },
    { year: 2027, revenue: 8304000000, growth: 0.05, ebit: 2028000000, ebitMargin: 0.24, nopat: 1662960000, da: 330000000, deltaWC: -56000000, capex: -380000000, ufcf: 1556960000 },
    { year: 2028, revenue: 8719000000, growth: 0.05, ebit: 2129000000, ebitMargin: 0.24, nopat: 1745780000, da: 340000000, deltaWC: -59000000, capex: -390000000, ufcf: 1636780000 },
  ],
  terminalValue: {
    method: 'Gordon',
    terminalGrowthRate: 0.035,
    exitMultiple: 15.0,
    value: 18500000000,
    pvOfTerminalValue: 10500000000
  },
  valuation: {
    pvOfForecast: 5500000000,
    enterpriseValue: 16000000000,
    netDebt: 1500000000,
    equityValue: 14500000000,
    sharesOutstanding: 290000000,
    fairValuePerShare: 94.51
  }
};

export const mockLogs: AgentLog[] = [
  { timestamp: "04:47:01", agent: "Planner", action: "Analyzing request for ticker A", details: "Plan: Collect 10-K, current price, and consensus estimates.", status: "success" },
  { timestamp: "04:47:05", agent: "Data Agent", action: "Fetching SEC EDGAR filings for Agilent", details: "Retrieved 10-K (2023), 10-Q (Q3 2024)", status: "success" },
  { timestamp: "04:47:10", agent: "Valuator", action: "Performing DCF calculation", details: "Calculated WACC: 11.17%, Fair Value: $94.51", status: "success" },
  { timestamp: "04:47:15", agent: "Critic", action: "Auditing valuation assumptions", details: "Warning: Terminal Growth Rate (3.5%) is at maximum threshold.", status: "warning" },
  { timestamp: "04:47:20", agent: "Revisor", action: "Adjusting revenue growth projections", details: "Updated 2024 growth to 5.0% based on management guidance.", status: "success" },
  { timestamp: "04:47:25", agent: "Reporter", action: "Generating final valuation report", details: "Document ready for download (Markdown, JSON)", status: "success" },
];

export const mockNews: NewsItem[] = [
  { title: "Agilent Q3 Results", date: "2024-03-20", source: "Yahoo", url: "#", excerpt: "Revenue down 5.6% YoY." },
  { title: "New LC/MS Systems", date: "2024-03-15", source: "PR Newswire", url: "#", excerpt: "Enhanced sensitivity for research." }
];

export const mockExcerpts: RAGExcerpt[] = [
  { category: "growth", content: "Focusing on high-growth biopharma markets.", document: "10-K 2023", page: 12 },
  { category: "risk", content: "Intense competition in life sciences.", document: "10-K 2023", page: 45 }
];

export const mockValidationIssues: ValidationIssue[] = [
  { rule: "Terminal Growth Upper Bound", severity: "medium", status: "resolved", message: "Initial terminal growth exceeded 3.5% US GDP cap.", resolution: "Revisor capped growth at 3.5% per Phase B mandate." },
  { rule: "EBIT Margin Consistency", severity: "low", status: "resolved", message: "2024 margin projection was inconsistent with historical average.", resolution: "Adjusted 2024 EBIT margin to 24% following management guidance audit." }
];

export const mockEvidenceAudits: EvidenceAudit[] = [
  { assumption: "Revenue Growth (2024)", value: "5.0%", source: "SEC 10-Q Q3 2024", evidenceText: "We expect high single-digit and mid-single-digit growth across our core segments in FY24.", confidence: 9 },
  { assumption: "WACC (Risk-Free Rate)", value: "4.2%", source: "US Treasury 10Y", evidenceText: "Yield on 10-year Treasury notes as of 2024-03-22.", confidence: 10 }
];

export const mockReport: ValuationReport = {
  companyName: "Agilent Technologies",
  ticker: "A",
  methodsUsed: ["DCF (Unlevered)", "Comparable Multiples"],
  keyInputs: ["Net Income: $1.24B", "FCF: $1.15B"],
  coreAssumptions: [
    { label: "WACC", value: 11.17, unit: '%', source: "CAPM", rationale: "Based on 1.1 beta." },
    { label: "Terminal Growth", value: 3.5, unit: '%', source: "GDP", rationale: "Long-term US GDP growth." }
  ],
  evidenceSources: ["SEC 10-K 2023", "Earnings Call"],
  valuationRange: { low: 85.20, base: 94.51, high: 105.30 },
  fairValue: 94.51,
  confidenceScore: 8,
  riskFactors: ["Market volatility"],
  critiqueComments: ["Model sensitive to WACC."]
};
