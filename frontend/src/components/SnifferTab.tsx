import { useEffect, useRef, useState } from 'react';
import { useStore } from '../store';
import type { SnifferTrace } from '../store';
import { API_BASE_URL } from '../config';

export function SnifferTab() {
    const {
        snifferLogs,
        snifferFilter,
        addSnifferLog,
        setSnifferFilter,
        clearSnifferLogs,
    } = useStore();

    const eventSourceRef = useRef<EventSource | null>(null);
    const [expandedId, setExpandedId] = useState<string | null>(null);

    // SSE Connection
    useEffect(() => {
        const es = new EventSource(`${API_BASE_URL}/v1/sniffer/stream`);
        eventSourceRef.current = es;

        es.onmessage = (event) => {
            try {
                const trace: SnifferTrace = JSON.parse(event.data);
                addSnifferLog(trace);
            } catch {
                // heartbeat or malformed — ignore
            }
        };

        es.onerror = () => {
            // EventSource auto-reconnects
        };

        return () => {
            es.close();
            eventSourceRef.current = null;
        };
    }, [addSnifferLog]);

    // Apply filters
    const filtered = snifferLogs.filter((t) => {
        if (snifferFilter.status !== 'ALL' && t.firewall.decision !== snifferFilter.status) {
            return false;
        }
        if (snifferFilter.filterType !== 'ALL') {
            const hasStage = t.firewall.pipeline_trace.some(
                (s) => s.stage === snifferFilter.filterType
            );
            if (!hasStage) return false;
        }
        return true;
    });

    const formatTime = (iso: string) => {
        try {
            const d = new Date(iso);
            return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch {
            return iso;
        }
    };

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case 'COMPLETED': return 'sniffer-status-completed';
            case 'BREACH': return 'sniffer-status-breach';
            default: return 'sniffer-status-pending';
        }
    };

    return (
        <div className="sniffer-tab panel" id="sniffer-tab">
            <div className="sniffer-header">
                <h2>🔍 RTSS — Full Payload Inspector</h2>
                <div className="sniffer-controls">
                    <div className="sniffer-filter-group">
                        <label>Decision:</label>
                        <select
                            id="sniffer-status-filter"
                            value={snifferFilter.status}
                            onChange={(e) => setSnifferFilter({ status: e.target.value as 'ALL' | 'PASS' | 'BREACH' })}
                        >
                            <option value="ALL">ALL</option>
                            <option value="PASS">PASS</option>
                            <option value="BREACH">BREACH</option>
                        </select>
                    </div>
                    <div className="sniffer-filter-group">
                        <label>Stage:</label>
                        <select
                            id="sniffer-stage-filter"
                            value={snifferFilter.filterType}
                            onChange={(e) => setSnifferFilter({ filterType: e.target.value as 'ALL' | 'noise' | 'cosine' | 'excitation' })}
                        >
                            <option value="ALL">ALL</option>
                            <option value="noise">Noise</option>
                            <option value="cosine">Cosine</option>
                            <option value="excitation">Excitation</option>
                        </select>
                    </div>
                    <button id="sniffer-clear-btn" className="sniffer-clear-btn" onClick={clearSnifferLogs}>
                        Clear
                    </button>
                </div>
            </div>

            <div className="sniffer-stats">
                <span className="sniffer-stat-total">{snifferLogs.length} traces</span>
                <span className="sniffer-stat-pass">
                    ✓ {snifferLogs.filter(t => t.firewall.decision === 'PASS').length}
                </span>
                <span className="sniffer-stat-breach">
                    ✕ {snifferLogs.filter(t => t.firewall.decision === 'BREACH').length}
                </span>
                <span className="sniffer-stat-showing">Showing: {filtered.length}</span>
            </div>

            <div className="sniffer-log-list">
                {filtered.length === 0 ? (
                    <div className="sniffer-empty">
                        Waiting for telemetry…<br />
                        <span className="sniffer-empty-hint">
                            Send a request to POST /v1/chat/completions with the firewall enabled.
                        </span>
                    </div>
                ) : (
                    filtered.map((trace) => (
                        <div
                            key={trace.id}
                            className={`sniffer-entry sniffer-entry-${trace.firewall.decision.toLowerCase()}`}
                            id={`sniffer-trace-${trace.id}`}
                        >
                            <div
                                className="sniffer-entry-header sniffer-entry-clickable"
                                onClick={() => setExpandedId(expandedId === trace.id ? null : trace.id)}
                            >
                                <span className="sniffer-time">{formatTime(trace.timestamp)}</span>
                                <span className={`sniffer-badge sniffer-badge-${trace.firewall.decision.toLowerCase()}`}>
                                    {trace.firewall.decision}
                                </span>
                                <span className="sniffer-model">{trace.request.model}</span>
                                <span className={`sniffer-status-badge ${getStatusBadgeClass(trace.status)}`}>
                                    {trace.status || 'PENDING'}
                                </span>
                                <span className="sniffer-expand-icon">
                                    {expandedId === trace.id ? '▼' : '▶'}
                                </span>
                            </div>
                            <div className="sniffer-entry-message">
                                "{trace.request.last_message.slice(0, 80)}{trace.request.last_message.length > 80 ? '…' : ''}"
                            </div>
                            <div className="sniffer-pipeline">
                                {trace.firewall.pipeline_trace.map((stage, i) => (
                                    <span
                                        key={i}
                                        className={`sniffer-stage ${stage.passed ? 'sniffer-stage-pass' : 'sniffer-stage-breach'}`}
                                    >
                                        {stage.stage}: {stage.value.toFixed(stage.stage === 'excitation' ? 0 : 3)}
                                        {' / '}
                                        {stage.threshold.toFixed(stage.stage === 'excitation' ? 0 : 3)}
                                        {stage.passed ? ' ✓' : ' ✕'}
                                    </span>
                                ))}
                            </div>
                            {trace.response_preview && !expandedId && (
                                <div className="sniffer-preview">
                                    ↳ {trace.response_preview}
                                </div>
                            )}
                            {expandedId === trace.id && (
                                <div className="sniffer-expanded-panel">
                                    <div className="sniffer-expanded-section">
                                        <p className="sniffer-expanded-label">📨 Request History ({trace.request.request_history?.length || 0} messages)</p>
                                        <pre className="sniffer-expanded-json">
                                            {JSON.stringify(trace.request.request_history || [], null, 2)}
                                        </pre>
                                    </div>
                                    <div className="sniffer-expanded-section">
                                        <p className="sniffer-expanded-label sniffer-expanded-label-response">📝 Full Response</p>
                                        <pre className="sniffer-expanded-response">
                                            {trace.response_content || (trace.status === 'PENDING' ? '⏳ Streaming…' : '(empty)')}
                                        </pre>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
