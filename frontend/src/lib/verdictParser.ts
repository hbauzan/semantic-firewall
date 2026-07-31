/** Parse firewall audit blocks into human-readable verdict cards. */

export type VerdictDecision = 'pass' | 'block' | 'raw';

export interface ParsedVerdict {
  decision: VerdictDecision;
  headline: string;
  summary: string;
  metrics: string;
  pipeline: string;
  segment: string;
  body: string;
  tuningHint?: string;
  recommendedTargets?: {
    cosine?: number;
    excitation?: number;
    noise?: number;
  };
  ragSnippet?: string;
}

const REASON_LABELS: Record<string, string> = {
  cosine: 'Query is not similar enough to your document corpus.',
  excitation: 'Excitation filter threshold not met (insufficient activations).',
  noise: 'Prompt entropy looks like an adversarial burst pattern.',
  no_context: 'No corpus loaded — cannot verify this query.',
};

function humanReason(bareReason: string): string {
  return REASON_LABELS[bareReason] ?? `Blocked by filter: ${bareReason}`;
}

export function parseFirewallMessage(content: string): ParsedVerdict | null {
  if (!content.includes('[FIREWALL_AUDIT]')) {
    return null;
  }

  const isBlock = content.includes('[FW_BLOCK]');
  const isPass = content.includes('[FW_PASS]');

  let segment = '';
  const segMatch = content.match(/Segment:\s*"([^"]*)"/);
  if (segMatch) segment = segMatch[1];

  let metrics = '';
  const metricsMatch = content.match(/Metrics:([^\n]+)/);
  if (metricsMatch) metrics = metricsMatch[1].trim();

  let pipeline = '';
  const pipeMatch = content.match(/Pipeline:\s*\[([^\]]*)\]/);
  if (pipeMatch) pipeline = pipeMatch[1];

  let tuningHint = '';
  const hintMatch = content.match(/\[TUNING HINT\]([^\n]+)/);
  if (hintMatch) tuningHint = hintMatch[1].trim();

  let ragSnippet = '';
  const ragMatch = content.match(/RAG Match [^:]+:\s*"([^"]*)"/);
  if (ragMatch) ragSnippet = ragMatch[1].trim();

  const recommendedTargets: { cosine?: number; excitation?: number; noise?: number } = {};
  if (tuningHint) {
    const cosM = tuningHint.match(/Cosine\s*<=\s*([\d.]+)/i);
    if (cosM) recommendedTargets.cosine = parseFloat(cosM[1]);
    const excM = tuningHint.match(/Excitation\s*<=\s*([\d.]+)/i);
    if (excM) recommendedTargets.excitation = parseFloat(excM[1]);
    const noiseM = tuningHint.match(/Noise\s*<=\s*([\d.]+)/i);
    if (noiseM) recommendedTargets.noise = parseFloat(noiseM[1]);
  }

  let body = '';
  const llmIdx = content.indexOf('[LLM_RESPONSE]:');
  if (llmIdx >= 0) {
    body = content.slice(llmIdx + '[LLM_RESPONSE]:'.length).trim();
  }

  if (isBlock) {
    let bareReason = 'unknown';
    if (metrics.toLowerCase().includes('cosine')) bareReason = 'cosine';
    else if (metrics.toLowerCase().includes('entropy')) bareReason = 'noise';
    else if (metrics.toLowerCase().includes('excitation') || metrics.toLowerCase().includes('resonance')) bareReason = 'excitation';
    else if (metrics.toLowerCase().includes('no_context')) bareReason = 'no_context';

    return {
      decision: 'block',
      headline: 'Query blocked',
      summary: humanReason(bareReason),
      metrics,
      pipeline,
      segment,
      body: '',
      tuningHint,
      recommendedTargets,
      ragSnippet,
    };
  }

  if (isPass) {
    return {
      decision: 'pass',
      headline: 'Query allowed',
      summary: 'All firewall filters passed. The LLM answered below.',
      metrics,
      pipeline,
      segment: '',
      body,
      tuningHint,
      recommendedTargets,
      ragSnippet,
    };
  }

  return {
    decision: 'raw',
    headline: 'Firewall audit',
    summary: '',
    metrics,
    pipeline,
    segment,
    body: content,
    tuningHint,
    recommendedTargets,
    ragSnippet,
  };
}
