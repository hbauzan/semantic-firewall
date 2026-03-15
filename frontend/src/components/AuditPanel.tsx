import React, { useState } from 'react';

export const AuditPanel: React.FC = () => {
    const [auditQuery, setAuditQuery] = useState('');
    const [auditResult, setAuditResult] = useState<{ activations: number, text: string } | null>(null);

    const runAudit = async () => {
        if (!auditQuery.trim()) return;
        try {
            const res = await fetch('http://localhost:8000/audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: auditQuery })
            });
            const data = await res.json();
            setAuditResult(data);
        } catch (err) {
            console.error("Audit failed", err);
        }
    };

    return (
        <div className="panel audit-panel" style={{ marginTop: '1rem', flexShrink: 0 }}>
            <h2 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Stress Test Query (Audit)</h2>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <input
                    type="text"
                    value={auditQuery}
                    onChange={(e) => setAuditQuery(e.target.value)}
                    style={{ flexGrow: 1, background: '#000', color: 'var(--text-main)', border: '1px solid var(--border)', padding: '0.5rem' }}
                    placeholder="Enter audit check query..."
                    onKeyDown={(e) => e.key === 'Enter' && runAudit()}
                />
                <button onClick={runAudit}>Audit</button>
            </div>
            {auditResult && (
                <div style={{ background: '#000', padding: '0.5rem', border: '1px solid var(--border)', fontSize: '0.9rem' }}>
                    <div><strong>Activations (Geometric Nodes Hit):</strong> {auditResult.activations}</div>
                    <div style={{ marginTop: '0.5rem', maxHeight: '100px', overflowY: 'auto' }}>
                        <small>{auditResult.text}</small>
                    </div>
                </div>
            )}
        </div>
    );
};
