import React from 'react';
import { parseFirewallMessage } from '../lib/verdictParser';

interface VerdictCardProps {
  content: string;
  role: string;
}

export const VerdictCard: React.FC<VerdictCardProps> = ({ content, role }) => {
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
        {verdict.pipeline && (
          <div className="verdict-pipeline">
            <span className="verdict-metrics-label">Pipeline</span>
            {verdict.pipeline}
          </div>
        )}
      </div>
    );
  }

  return <div className={`chat-message ${role}`}>{content}</div>;
};
