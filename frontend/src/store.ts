import { create, StateCreator } from 'zustand';

// ============================================================
// Slice Interfaces
// ============================================================

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface TelemetryData {
  cpu: number;
  ram: number;
  gpu: number;
}

interface PipelineStageTrace {
  stage: string;
  passed: boolean;
  value: number;
  threshold: number;
}

export interface SnifferTrace {
  id: string;
  timestamp: string;
  request: {
    model: string;
    last_message: string;
    request_history: Array<{ role: string; content: string }>;
  };
  firewall: {
    decision: 'PASS' | 'BREACH';
    pipeline_trace: PipelineStageTrace[];
  };
  response_preview: string;
  response_content: string;
  status: 'PENDING' | 'COMPLETED' | 'BREACH';
}

interface SnifferFilter {
  status: 'ALL' | 'PASS' | 'BREACH';
  filterType: 'ALL' | 'noise' | 'cosine' | 'excitation';
}

// --- Firewall Slice ---
export interface FirewallSlice {
  excitationThreshold: number;
  noiseTolerance: number;
  cosineThreshold: number;
  globalNoiseLimit: number;
  cosineOrder: number;
  excitationOrder: number;
  noiseOrder: number;
  adaptiveFactor: number;
  ragTopK: number;
  noiseEnabled: boolean;
  cosineEnabled: boolean;
  excitationEnabled: boolean;
  firewallMode: 'positive' | 'negative';
  activeTab: 'chat' | 'sniffer';
  upstreamProvider: 'ollama' | 'google' | 'openai' | 'anthropic' | 'groq';
  setExcitationThreshold: (val: number) => void;
  setNoiseTolerance: (val: number) => void;
  setCosineThreshold: (val: number) => void;
  setGlobalNoiseLimit: (val: number) => void;
  setCosineOrder: (val: number) => void;
  setExcitationOrder: (val: number) => void;
  setNoiseOrder: (val: number) => void;
  setAdaptiveFactor: (val: number) => void;
  setRagTopK: (val: number) => void;
  setNoiseEnabled: (val: boolean) => void;
  setCosineEnabled: (val: boolean) => void;
  setExcitationEnabled: (val: boolean) => void;
  setFirewallMode: (val: 'positive' | 'negative') => void;
  setActiveTab: (val: 'chat' | 'sniffer') => void;
  setUpstreamProvider: (val: 'ollama' | 'google' | 'openai' | 'anthropic' | 'groq') => void;
}

// --- Chat Slice ---
export interface ChatSlice {
  messages: Message[];
  addMessage: (msg: Message) => void;
  clearMessages: () => void;
}

// --- System Slice (telemetry, ingestion, global status) ---
export interface SystemSlice {
  telemetry: TelemetryData;
  setTelemetry: (data: TelemetryData) => void;
  systemAction: string;
  setSystemAction: (action: string) => void;
  ingestionStatus: {
    taskId: string | null;
    status: string;
    progress: number;
    message: string;
  };
  setIngestionStatus: (status: Partial<SystemSlice['ingestionStatus']>) => void;
}

// --- Sniffer Slice ---
export interface SnifferSlice {
  snifferLogs: SnifferTrace[];
  snifferFilter: SnifferFilter;
  addSnifferLog: (trace: SnifferTrace) => void;
  updateSnifferLog: (trace: SnifferTrace) => void;
  setSnifferFilter: (filter: Partial<SnifferFilter>) => void;
  clearSnifferLogs: () => void;
}

// ============================================================
// Combined Store Type
// ============================================================

export type StoreState = FirewallSlice & ChatSlice & SystemSlice & SnifferSlice;

// ============================================================
// Slice Creators
// ============================================================

const createFirewallSlice: StateCreator<StoreState, [], [], FirewallSlice> = (set) => ({
  excitationThreshold: 150,
  noiseTolerance: 0.005,
  cosineThreshold: 0.50,
  globalNoiseLimit: 0.50,
  cosineOrder: 2,
  excitationOrder: 3,
  noiseOrder: 1,
  adaptiveFactor: 0.85,
  ragTopK: 3,
  noiseEnabled: true,
  cosineEnabled: true,
  excitationEnabled: true,
  firewallMode: 'positive',
  activeTab: 'chat',
  upstreamProvider: 'ollama',
  setExcitationThreshold: (val) => set({ excitationThreshold: val }),
  setNoiseTolerance: (val) => set({ noiseTolerance: val }),
  setCosineThreshold: (val) => set({ cosineThreshold: val }),
  setGlobalNoiseLimit: (val) => set({ globalNoiseLimit: val }),
  setCosineOrder: (val) => set({ cosineOrder: val }),
  setExcitationOrder: (val) => set({ excitationOrder: val }),
  setNoiseOrder: (val) => set({ noiseOrder: val }),
  setAdaptiveFactor: (val) => set({ adaptiveFactor: val }),
  setRagTopK: (val) => set({ ragTopK: val }),
  setNoiseEnabled: (val) => set({ noiseEnabled: val }),
  setCosineEnabled: (val) => set({ cosineEnabled: val }),
  setExcitationEnabled: (val) => set({ excitationEnabled: val }),
  setFirewallMode: (val) => set({ firewallMode: val }),
  setActiveTab: (val) => set({ activeTab: val }),
  setUpstreamProvider: (val) => set({ upstreamProvider: val }),
});

const createChatSlice: StateCreator<StoreState, [], [], ChatSlice> = (set) => ({
  messages: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  clearMessages: () => set({ messages: [] }),
});

const createSystemSlice: StateCreator<StoreState, [], [], SystemSlice> = (set) => ({
  telemetry: { cpu: 0, ram: 0, gpu: 0 },
  setTelemetry: (data) => set({ telemetry: data }),
  systemAction: 'SYSTEM IDLE',
  setSystemAction: (action) => set({ systemAction: action }),
  ingestionStatus: { taskId: null, status: 'idle', progress: 0, message: '' },
  setIngestionStatus: (status) => set((state) => ({
    ingestionStatus: { ...state.ingestionStatus, ...status }
  })),
});

const createSnifferSlice: StateCreator<StoreState, [], [], SnifferSlice> = (set) => ({
  snifferLogs: [],
  snifferFilter: { status: 'ALL', filterType: 'ALL' },
  addSnifferLog: (trace) => set((state) => {
    const existingIdx = state.snifferLogs.findIndex(t => t.id === trace.id);
    if (existingIdx !== -1) {
      const updated = [...state.snifferLogs];
      updated[existingIdx] = trace;
      return { snifferLogs: updated };
    }
    const logs = [trace, ...state.snifferLogs].slice(0, 100);
    return { snifferLogs: logs };
  }),
  updateSnifferLog: (trace) => set((state) => {
    const updated = state.snifferLogs.map(t => t.id === trace.id ? trace : t);
    return { snifferLogs: updated };
  }),
  setSnifferFilter: (filter) => set((state) => ({
    snifferFilter: { ...state.snifferFilter, ...filter }
  })),
  clearSnifferLogs: () => set({ snifferLogs: [] }),
});

// ============================================================
// Unified Store (API-compatible — no consumer changes required)
// ============================================================

export const useStore = create<StoreState>()((...a) => ({
  ...createFirewallSlice(...a),
  ...createChatSlice(...a),
  ...createSystemSlice(...a),
  ...createSnifferSlice(...a),
}));
