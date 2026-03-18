import { create } from 'zustand';

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

interface StoreState {
  excitationThreshold: number;
  noiseTolerance: number;
  cosineThreshold: number;
  globalNoiseLimit: number;
  cosineOrder: number;
  excitationOrder: number;
  noiseOrder: number;
  adaptiveFactor: number;
  noiseEnabled: boolean;
  cosineEnabled: boolean;
  excitationEnabled: boolean;
  setExcitationThreshold: (val: number) => void;
  setNoiseTolerance: (val: number) => void;
  setCosineThreshold: (val: number) => void;
  setGlobalNoiseLimit: (val: number) => void;
  setCosineOrder: (val: number) => void;
  setExcitationOrder: (val: number) => void;
  setNoiseOrder: (val: number) => void;
  setAdaptiveFactor: (val: number) => void;
  setNoiseEnabled: (val: boolean) => void;
  setCosineEnabled: (val: boolean) => void;
  setExcitationEnabled: (val: boolean) => void;

  messages: Message[];
  addMessage: (msg: Message) => void;
  clearMessages: () => void;

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
  setIngestionStatus: (status: Partial<StoreState['ingestionStatus']>) => void;
}

export const useStore = create<StoreState>((set) => ({
  excitationThreshold: 150,
  noiseTolerance: 0.005,
  cosineThreshold: 0.50,
  globalNoiseLimit: 0.50,
  cosineOrder: 2,
  excitationOrder: 3,
  noiseOrder: 1,
  adaptiveFactor: 0.85,
  noiseEnabled: true,
  cosineEnabled: true,
  excitationEnabled: true,
  setExcitationThreshold: (val) => set({ excitationThreshold: val }),
  setNoiseTolerance: (val) => set({ noiseTolerance: val }),
  setCosineThreshold: (val) => set({ cosineThreshold: val }),
  setGlobalNoiseLimit: (val) => set({ globalNoiseLimit: val }),
  setCosineOrder: (val) => set({ cosineOrder: val }),
  setExcitationOrder: (val) => set({ excitationOrder: val }),
  setNoiseOrder: (val) => set({ noiseOrder: val }),
  setAdaptiveFactor: (val) => set({ adaptiveFactor: val }),
  setNoiseEnabled: (val) => set({ noiseEnabled: val }),
  setCosineEnabled: (val) => set({ cosineEnabled: val }),
  setExcitationEnabled: (val) => set({ excitationEnabled: val }),

  messages: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  clearMessages: () => set({ messages: [] }),

  telemetry: { cpu: 0, ram: 0, gpu: 0 },
  setTelemetry: (data) => set({ telemetry: data }),

  systemAction: 'SYSTEM IDLE',
  setSystemAction: (action) => set({ systemAction: action }),

  ingestionStatus: { taskId: null, status: 'idle', progress: 0, message: '' },
  setIngestionStatus: (status) => set((state) => ({
    ingestionStatus: { ...state.ingestionStatus, ...status }
  })),
}));
