import { create, type StateCreator } from 'zustand';
import { persist } from 'zustand/middleware';

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
  status: 'PENDING' | 'COMPLETED' | 'BREACH' | 'ERROR';
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
  snifferViewLimit: number;
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
  setSnifferViewLimit: (val: number) => void;
}

// --- Chat Slice ---
export interface ChatSlice {
  messages: Message[];
  addMessage: (msg: Message) => void;
  clearMessages: () => void;
}

// --- System Slice (telemetry, ingestion, global status) ---

export type BackendHealthStatus = 'checking' | 'ok' | 'offline';

export interface BackendHealth {
  status: BackendHealthStatus;
  hint: string;
  checkedAt: number;
}

export type ActiveTaskKind = 'upload' | 'calibrate';

export interface ActiveTask {
  kind: ActiveTaskKind;
  title: string;
  phase: string;
  /** 0–100, or null for indeterminate (e.g. calibration sweep). */
  progress: number | null;
  startedAt: number;
  lastUpdateAt: number;
  stalled: boolean;
}

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
  backendHealth: BackendHealth;
  setBackendHealth: (health: BackendHealth) => void;
  activeTask: ActiveTask | null;
  startTask: (task: {
    kind: ActiveTaskKind;
    title: string;
    phase: string;
    progress?: number | null;
  }) => void;
  updateTask: (patch: Partial<Pick<ActiveTask, 'phase' | 'progress' | 'stalled'>>) => void;
  finishTask: (outcome: 'success' | 'error', message: string) => void;
  clearTask: () => void;
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
  cosineThreshold: 0.5315,
  globalNoiseLimit: 4.5,
  cosineOrder: 2,
  excitationOrder: 3,
  noiseOrder: 1,
  adaptiveFactor: 0.85,
  ragTopK: 12,
  noiseEnabled: true,
  cosineEnabled: true,
  excitationEnabled: true,
  firewallMode: 'positive',
  activeTab: 'chat',
  upstreamProvider: 'ollama',
  snifferViewLimit: 10,
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
  setSnifferViewLimit: (val) => set({ snifferViewLimit: val }),
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
  backendHealth: {
    status: 'checking',
    hint: 'Checking backend…',
    checkedAt: 0,
  },
  setBackendHealth: (health) => set({ backendHealth: health }),
  activeTask: null,
  startTask: (task) => {
    const now = Date.now();
    set({
      activeTask: {
        kind: task.kind,
        title: task.title,
        phase: task.phase,
        progress: task.progress ?? null,
        startedAt: now,
        lastUpdateAt: now,
        stalled: false,
      },
    });
  },
  updateTask: (patch) => set((state) => {
    if (!state.activeTask) return state;
    const now = Date.now();
    return {
      activeTask: {
        ...state.activeTask,
        ...patch,
        lastUpdateAt: now,
      },
    };
  }),
  finishTask: (outcome, message) => {
    set({
      activeTask: null,
      systemAction: message,
    });
    if (outcome === 'error') {
      setTimeout(() => set({ systemAction: 'SYSTEM IDLE' }), 5000);
    } else {
      setTimeout(() => set({ systemAction: 'SYSTEM IDLE' }), 4000);
    }
  },
  clearTask: () => set({ activeTask: null }),
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
    const logs = [trace, ...state.snifferLogs].slice(0, 1000);
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

export const useStore = create<StoreState>()(
  persist(
    (...a) => ({
      ...createFirewallSlice(...a),
      ...createChatSlice(...a),
      ...createSystemSlice(...a),
      ...createSnifferSlice(...a),
    }),
    {
      name: 'firewall-chat-storage',
      partialize: (state) => ({ messages: state.messages } as any),
    }
  )
);
