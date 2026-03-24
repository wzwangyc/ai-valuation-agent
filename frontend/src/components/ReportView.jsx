import React from 'react';

const ReportView = ({ report }) => {
  if (!report) return null;

  const buildMarkdown = () => {
    const cpName = report['Company Name'] || 'Unknown';
    const valMethod = report['Valuation Method'] || 'N/A';
    
    // Key inputs formatting
    const rev = report['Key Inputs']['Revenue (LTM)'] ? `$${(report['Key Inputs']['Revenue (LTM)'] / 1e9).toFixed(1)}B` : 'N/A';
    const ebit = report['Key Inputs']['EBIT (LTM)'] ? `$${(report['Key Inputs']['EBIT (LTM)'] / 1e9).toFixed(1)}B` : 'N/A';
    const opMarg = report['Key Inputs']['Operating Margin'] ? `${(report['Key Inputs']['Operating Margin'] * 100).toFixed(1)}%` : 'N/A';
    const pe = report['Key Inputs']['P/E (Trailing)'] ? `${parseFloat(report['Key Inputs']['P/E (Trailing)']).toFixed(1)}x` : 'N/A';
    const keysStr = `Revenue: ${rev}, EBIT: ${ebit}, Operating Margin: ${opMarg}, Trailing P/E: ${pe}`;
    
    // Assumptions formatting
    const wacc = report['Assumptions']['WACC'] || 'N/A';
    const tg = report['Assumptions']['Applied Terminal Growth Rate'] || 'N/A';
    const coe = report['Assumptions']['Cost of Equity'] || 'N/A';
    const rf = report['Assumptions']['Risk-Free Rate'] || 'N/A';
    const assumpStr = `WACC: ${wacc}, Terminal Growth: ${tg}, Cost of Equity: ${coe}, Rf: ${rf}`;

    // Evidence
    let evidenceStr = "Multiple Sources Used";
    if (report['Evidence Sources'] && report['Evidence Sources'].length) {
      if (report['Evidence Sources'].length > 3) {
        evidenceStr = `${report['Evidence Sources'].length} active sources including Yahoo Finance, FRED, SEC`;
      } else {
        evidenceStr = report['Evidence Sources'].join(', ');
      }
    }

    // Target Prices
    const optPrice = report['Target Price/Range']['Overall Valuation Range'] ? report['Target Price/Range']['Overall Valuation Range'].split('–')[1] || 'N/A' : 'N/A';
    const pssPrice = report['Target Price/Range']['Overall Valuation Range'] ? report['Target Price/Range']['Overall Valuation Range'].split('–')[0] || 'N/A' : 'N/A';
    const targetStr = `Optimistic: ${optPrice.trim()}, Base: ${report['Target Price/Range']['DCF Fair Price'] || 'N/A'}, Pessimistic: ${pssPrice.trim()}`;

    // Confidence
    const confStr = report['Confidence Level'] || 'N/A';
    
    // Risks
    const riskStr = (report['Risk Factors'] || []).join(', ') || 'N/A';
    
    // Critique
    const crit = report['Critique Comments'] ? report['Critique Comments'].replace(/\n/g, ' ') : 'N/A';
    
    // LLM Critique
    const llmCrit = report['LLM Analyst Critique'] ? report['LLM Analyst Critique'].replace(/\n/g, ' ') : 'N/A';

    return `\`\`\`markdown
# Valuation Report: ${cpName}

| Field              | Value                                                                 |
| ------------------ | --------------------------------------------------------------------- |
| Company Name       | ${cpName.padEnd(69)} |
| Valuation Method   | ${valMethod.padEnd(69)} |
| Key Inputs         | ${keysStr.padEnd(69)} |
| Assumptions        | ${assumpStr.padEnd(69)} |
| Evidence Sources   | ${evidenceStr.substring(0,66).padEnd(69)} |
| Target Price/Range | ${targetStr.padEnd(69)} |
| Confidence Level   | ${confStr.padEnd(69)} |
| Risk Factors       | ${(riskStr.substring(0,66)+'...').padEnd(69)} |
| Critique Comments  | ${(crit.substring(0,66)+'...').padEnd(69)} |
| LLM Analyst Critique| ${(llmCrit.substring(0,66)+'...').padEnd(69)} |
\`\`\``;
  };

  return (
    <div className="p-4 bg-bb-bg text-bb-green font-mono text-sm whitespace-pre overflow-x-auto border-b border-bb-light-gray leading-tight">
      {buildMarkdown()}
    </div>
  );
};

export default ReportView;
