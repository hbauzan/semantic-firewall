import { create } from 'zustand';

interface Message {
  id: number;
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
  setExcitationThreshold: (val: number) => void;
  setNoiseTolerance: (val: number) => void;
  
  messages: Message[];
  addMessage: (msg: Message) => void;
  clearMessages: () => void;
  
  telemetry: TelemetryData;
  setTelemetry: (data: TelemetryData) => void;
  
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
  setExcitationThreshold: (val) => set({ excitationThreshold: val }),
  setNoiseTolerance: (val) => set({ noiseTolerance: val }),
  
  messages: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  clearMessages: () => set({ messages: [] }),
  
  telemetry: { cpu: 0, ram: 0, gpu: 0 },
  setTelemetry: (data) => set({ telemetry: data }),
  
  ingestionStatus: { taskId: null, status: 'idle', progress: 0, message: '' },
  setIngestionStatus: (status) => set((state) => ({ 
    ingestionStatus: { ...state.ingestionStatus, ...status } 
  })),
}));
