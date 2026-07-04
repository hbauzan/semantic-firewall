import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import { API_BASE_URL } from '../config';
import { useBackendHealth } from '../hooks/useBackendHealth';
import { TaskProgressBar } from './TaskProgressBar';
import '../styles/ControlPanel.css';

const ALIVE_FRAMES = [
  [`  .-.  `, ` (o.o) `, `  >m<  `],
  [`  .-.  `, ` (o.-) `, `  >m<  `],
  [`  .-.  `, ` (-.o) `, `  >O<  `],
];

const DEAD_FRAME = [`  .-.  `, ` (x.x) `, `  >-<  `];

const UPLOAD_STALL_MS = 25_000;
const CALIBRATE_STALL_MS = 120_000;

interface MonkeyHeadProps {
  alive: boolean;
  label: string;
  frameIdx: number;
}

const MonkeyHead: React.FC<MonkeyHeadProps> = ({ alive, label, frameIdx }) => {
  const lines = alive ? ALIVE_FRAMES[frameIdx % ALIVE_FRAMES.length] : DEAD_FRAME;
  return (
    <div className={`monkey-head ${alive ? 'monkey-head--alive' : 'monkey-head--dead'}`}>
      <pre>{lines.join('\n')}</pre>
      <div className="monkey-label">{label}</div>
    </div>
  );
};

function apiStatusLabel(status: string, stalled: boolean, working: boolean): string {
  if (stalled) return 'STALLED';
  if (working) return 'WORKING';
  if (status === 'ok') return 'ONLINE';
  if (status === 'offline') return 'OFFLINE';
  return 'CHECKING';
}

export const TelemetryHUD: React.FC = () => {
  const {
    telemetry,
    setTelemetry,
    systemAction,
    noiseEnabled,
    cosineEnabled,
    excitationEnabled,
    backendHealth,
    activeTask,
  } = useStore();

  const [frameIdx, setFrameIdx] = useState(0);
  useBackendHealth();

  const monkeysAlive =
    backendHealth.status === 'ok' && !(activeTask?.stalled);
  const taskBusy = activeTask !== null && !activeTask.stalled;

  useEffect(() => {
    if (!monkeysAlive && !taskBusy) return;
    const animationInterval = setInterval(() => {
      setFrameIdx((prev) => (prev + 1) % ALIVE_FRAMES.length);
    }, taskBusy ? 350 : 500);
    return () => clearInterval(animationInterval);
  }, [monkeysAlive, taskBusy]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/system/stats`);
        if (!res.ok) return;
        const data = await res.json();
        setTelemetry(data);
      } catch (err) {
        console.error('Failed to fetch stats', err);
      }
    };

    const statsInterval = setInterval(fetchStats, 1000);
    fetchStats();
    return () => clearInterval(statsInterval);
  }, [setTelemetry]);

  // Stall detection: no progress heartbeat while a task is running
  useEffect(() => {
    const tick = setInterval(() => {
      const task = useStore.getState().activeTask;
      if (!task) return;
      const stallMs = task.kind === 'upload' ? UPLOAD_STALL_MS : CALIBRATE_STALL_MS;
      const idleFor = Date.now() - task.lastUpdateAt;
      const shouldStall = idleFor > stallMs;
      if (shouldStall !== task.stalled) {
        useStore.getState().updateTask({ stalled: shouldStall });
      }
    }, 2000);
    return () => clearInterval(tick);
  }, []);

  const apiWorking =
    backendHealth.status === 'ok' && activeTask !== null && !activeTask.stalled;

  const apiLabel = apiStatusLabel(
    backendHealth.status,
    Boolean(activeTask?.stalled),
    apiWorking,
  );
  const apiClass =
    activeTask?.stalled ? 'api-status--stalled'
      : apiWorking ? 'api-status--working'
        : backendHealth.status === 'ok' ? 'api-status--ok'
          : backendHealth.status === 'offline' ? 'api-status--offline'
            : 'api-status--checking';

  const sysDisplay = activeTask
    ? `${activeTask.title} · ${activeTask.phase}${activeTask.progress !== null ? ` (${Math.round(activeTask.progress)}%)` : ''}`
    : systemAction;

  const guidance = activeTask?.stalled
    ? 'No progress — check the backend terminal for errors or restart ./run_server.sh'
    : backendHealth.status === 'offline'
      ? backendHealth.hint
      : activeTask
        ? (activeTask.kind === 'calibrate'
          ? 'Calibration runs on the backend (embedder + 2D sweep) — may take 1–3 min'
          : 'Ingestion runs on the backend — watch progress below')
        : backendHealth.hint;

  return (
    <div className="panel hud-panel">
      <h2 className="hud-title">Three-Headed Semantic Firewall</h2>
      <p className="hud-subtitle">Geometric prompt gate · local-first</p>

      <div className="monkey-row">
        <MonkeyHead alive={monkeysAlive && noiseEnabled} label="NOISE" frameIdx={frameIdx} />
        <MonkeyHead alive={monkeysAlive && cosineEnabled} label="COSINE" frameIdx={frameIdx + 1} />
        <MonkeyHead alive={monkeysAlive && excitationEnabled} label="EXCITE" frameIdx={frameIdx + 2} />
      </div>

      <div className={`api-status ${apiClass}`}>
        <span className="api-status-dot" aria-hidden />
        <span className="api-status-prefix">[API] </span>
        <span className="api-status-value">{apiLabel}</span>
        <span className="api-status-hint"> — {guidance}</span>
      </div>

      <div className={`system-state ${activeTask ? 'system-state--busy' : ''}`}>
        <span className="sys-prefix">[SYS] </span>
        <span className={`sys-value ${activeTask?.stalled ? 'sys-value--stalled' : ''}`}>
          {sysDisplay}
        </span>
      </div>

      {activeTask && (
        <div className="hud-task-progress">
          <TaskProgressBar
            progress={activeTask.progress}
            stalled={activeTask.stalled}
          />
        </div>
      )}

      <div className="telemetry-line">
        <span>CPU {telemetry.cpu.toFixed(0)}%</span>
        <span>RAM {telemetry.ram.toFixed(0)}MB</span>
        <span>GPU {telemetry.gpu.toFixed(0)}%</span>
      </div>
    </div>
  );
};
