import React, { useState } from 'react';
import { parseFirewallMessage } from '../lib/verdictParser';
import { useStore } from '../store';

interface VerdictCardProps {
  content: string;
  role: string;
}

export const VerdictCard: React.FC<VerdictCardProps> = ({ content, role }) => {
  const { setCosineThreshold, setExcitationThreshold, setGlobalNoiseLimit } = useStore();
  const [applied, setApplied] = useState(false);

  if (role === 'user') {
    return (
      <div className="chat-message user">
        <span className="msg-prefix">&gt;</span> {content}
      </div>
    );
  }

  const verdict = parseFirewallMessage(content);

  if (!verdict) {
    return <div className={`chat-message ${role}`}>{content}</div>;
  }

  const handleApplySliders = () => {
    if (!verdict.recommendedTargets) return;
    const { cosine, excitation, noise } = verdict.recommendedTargets;
    if (cosine !== undefined) setCosineThreshold(cosine);
    if (excitation !== undefined) setExcitationThreshold(excitation);
    if (noise !== undefined) setGlobalNoiseLimit(noise);
    setApplied(true);
  };

  const hasTargets = verdict.recommendedTargets && (
    verdict.recommendedTargets.cosine !== undefined ||
    verdict.recommendedTargets.excitation !== undefined ||
    verdict.recommendedTargets.noise !== undefined
  );

  if (verdict.decision === 'pass') {
    return (
      <div className={`chat-message ${role} verdict-card verdict-card--pass`}>
        <div className="verdict-headline">{verdict.headline}</div>
        <p className="verdict-summary">{verdict.summary}</p>
        {verdict.metrics && (
          <div className="verdict-metrics">
            <span className="verdict-metrics-label">Metrics</span>
            {verdict.metrics}
          </div>
        )}
        {verdict.ragSnippet && (
          <div className="verdict-rag-snippet" style={{ fontSize: '0.85em', opacity: 0.8, marginTop: '6px' }}>
            <span className="verdict-metrics-label">RAG Context Match</span>
            "{verdict.ragSnippet}"
          </div>
        )}
        {verdict.body && (
          <div className="verdict-llm-body">{verdict.body}</div>
        )}
      </div>
    );
  }

  if (verdict.decision === 'block') {
    return (
      <div className="chat-message system verdict-card verdict-card--block">
        <div className="verdict-headline">{verdict.headline}</div>
        <p className="verdict-summary">{verdict.summary}</p>
        {verdict.segment && (
          <div className="verdict-segment">
            <span className="verdict-metrics-label">Blocked clause</span>
            &ldquo;{verdict.segment}&rdquo;
          </div>
        )}
        {verdict.metrics && (
          <div className="verdict-metrics">
            <span className="verdict-metrics-label">Metrics</span>
            {verdict.metrics}
          </div>
        )}
        {verdict.tuningHint && (
          <div className="verdict-tuning-hint" style={{ marginTop: '8px', padding: '6px 10px', background: 'rgba(255, 165, 0, 0.1)', borderLeft: '3px solid #ffa500', borderRadius: '4px', fontSize: '0.9em' }}>
            <span style={{ color: '#ffa500', fontWeight: 'bold' }}>⚡ Tuning Recommendation: </span>
            {verdict.tuningHint}
          </div>
        )}
        {hasTargets && (
          <button
            onClick={handleApplySliders}
            disabled={applied}
            style={{
              marginTop: '10px',
              padding: '6px 12px',
              backgroundColor: applied ? '#2e7d32' : '#0288d1',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: applied ? 'default' : 'pointer',
              fontWeight: 'bold',
              fontSize: '0.85em',
            }}
          >
            {applied ? '✓ Sliders Updated' : '⚡ Apply Recommended Sliders to HUD'}
          </button>
        )}
        {verdict.ragSnippet && (
          <div className="verdict-rag-snippet" style={{ fontSize: '0.85em', opacity: 0.8, marginTop: '8px' }}>
            <span className="verdict-metrics-label">RAG Context Match</span>
            "{verdict.ragSnippet}"
          </div>
        )}
        {verdict.pipeline && (
          <div className="verdict-pipeline" style={{ marginTop: '8px' }}>
            <span className="verdict-metrics-label">Pipeline</span>
            {verdict.pipeline}
          </div>
        )}
      </div>
    );
  }

  return <div className={`chat-message ${role}`}>{content}</div>;
};
