/** Extract a human-readable message from FastAPI error bodies. */
export function parseApiError(body: string): string {
  if (!body.trim()) return 'Request failed';

  try {
    const json = JSON.parse(body) as { detail?: unknown };
    if (typeof json.detail === 'string') return json.detail;
    if (Array.isArray(json.detail)) {
      return json.detail.map((d) => String(d)).join('; ');
    }
  } catch {
    // not JSON — return raw text
  }

  return body;
}
