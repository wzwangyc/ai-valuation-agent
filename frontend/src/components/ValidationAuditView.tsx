import React from 'react';
import { CheckCircle, AlertTriangle, Link as LinkIcon } from 'lucide-react';

interface ValidationAuditViewProps {
  audits: any[];
  issues: any[];
}

const ValidationAuditView: React.FC<ValidationAuditViewProps> = ({ audits, issues }) => {
  return (
    <section className="section-container">
      <div className="flex flex-col gap-20">
        <div>
          <h2 className="text-4xl font-bold mb-12 text-center">Audited Accuracy.</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="apple-card">
              <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <CheckCircle className="text-apple-blue" size={20} />
                Evidence Audit
              </h3>
              <div className="space-y-4">
                {audits.map((audit, i) => (
                  <div key={i} className="flex justify-between items-center py-3 border-b border-apple-bg last:border-0">
                    <div>
                      <p className="font-medium text-sm">{audit.assumption}</p>
                      <p className="text-[11px] text-apple-gray uppercase tracking-widest">{audit.source}</p>
                    </div>
                    <LinkIcon size={14} className="text-apple-blue cursor-pointer" />
                  </div>
                ))}
              </div>
            </div>

            <div className="apple-card">
              <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <AlertTriangle className="text-orange-500" size={20} />
                Inconsistency Detection
              </h3>
              <div className="space-y-4">
                {issues.map((issue, i) => (
                  <div key={i} className="p-4 bg-apple-bg rounded-2xl">
                    <p className="text-sm font-medium mb-1">{issue.title}</p>
                    <p className="text-xs text-apple-gray">{issue.description}</p>
                    <div className="mt-2 text-[10px] bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full inline-block font-semibold uppercase">
                      Agent Revised
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ValidationAuditView;
