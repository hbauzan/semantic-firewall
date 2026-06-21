export interface TooltipEntry {
  what: string;
  how: string;
  suggested: string;
}

export const TOOLTIP_REGISTRY: Record<string, Record<string, TooltipEntry>> = {
  en: {
    upstream: {
      what: "Selects the active inference provider.",
      how: "Routes the sanitized prompt to the chosen cloud or local LLM engine.",
      suggested: "N/A"
    },
    mode: {
      what: "Toggles between Allowlist and Denylist logic.",
      how: "Positive: Only topics aligned with the corpus pass. Negative: Topics aligned with the corpus are blocked.",
      suggested: "Positive (Default)"
    },
    noise: {
      what: "Shannon Entropy analysis, detects spam and adversarial 'burst' attacks.",
      how: "Lower value: Allows repetitive text. Higher value: Requires natural, varied language.",
      suggested: "4.5 / 4.5"
    },
    cosine: {
      what: "Semantic similarity threshold gate.",
      how: "Lower: Lax (allows broad matches). Higher: Strict (requires exact semantic alignment).",
      suggested: "0.53 / 0.62"
    },
    excitation: {
      what: "Dimensional resonance count (1024D).",
      how: "Lower: Easier to pass. Higher: Requires more vector dimensions to align exactly.",
      suggested: "150 / 170"
    },
    tolerance: {
      what: "Sensitivity of individual dimension matching.",
      how: "Lower: Strict (dimensions must be nearly identical). Higher: Lax (allows variance).",
      suggested: "0.005 / 0.005"
    },
    adaptive: {
      what: "Dynamic threshold multiplier for short queries (fewer than 6 words).",
      how: "In Positive Mode, it lowers the excitation threshold (e.g., 0.85x) to provide 'forgiveness' for brief phrases that lack dense semantic data. In Negative Mode, it increases the similarity requirement (1.15x) to ensure short malicious commands are caught with higher confidence.",
      suggested: "0.85 / 0.85"
    },
    rag: {
      what: "Number of context chunks retrieved from the corpus.",
      how: "Lower: Faster, less context. Higher: Slower, provides the LLM with deeper, more grounded context.",
      suggested: "3 / 3"
    },
    seq: {
      what: "Execution order in the firewall pipeline.",
      how: "Determines evaluation sequence. Early failure short-circuits the process to save compute.",
      suggested: "1, 2, 3"
    },
    profiles: {
      what: "Persistent configuration snapshots.",
      how: "Saves or loads all slider and toggle states to/from JSON files.",
      suggested: "N/A"
    },
    corpus: {
      what: "PDF document ingestion system.",
      how: "Chunks and vectorizes documents for storage in the LanceDB vector database.",
      suggested: "N/A"
    }
  }
};
