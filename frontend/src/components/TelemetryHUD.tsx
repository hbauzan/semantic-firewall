import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import { API_BASE_URL } from '../config';
import '../styles/ControlPanel.css';

// Alive monkey frames (animated mouth)
const ALIVE_FRAMES = [
  [
    `  .-.  `,
    ` (o.o) `,
    `  >m<  `,
  ],
  [
    `  .-.  `,
    ` (o.-) `,
    `  >m<  `,
  ],
  [
    `  .-.  `,
    ` (-.o) `,
    `  >O<  `,
  ],
];

// Dead monkey (static)
const DEAD_FRAME = [
  `  .-.  `,
  ` (x.x) `,
  `  >-<  `,
];

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

export const TelemetryHUD: React.FC = () => {
  const { telemetry, setTelemetry, systemAction, noiseEnabled, cosineEnabled, excitationEnabled } = useStore();
  const [frameIdx, setFrameIdx] = useState(0);

  useEffect(() => {
    const animationInterval = setInterval(() => {
      setFrameIdx((prev) => (prev + 1) % ALIVE_FRAMES.length);
    }, 500);
    return () => clearInterval(animationInterval);
  }, []);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/system/stats`);
        if (!res.ok) return;
        const data = await res.json();
        setTelemetry(data);
      } catch (err) {
        console.error("Failed to fetch stats", err);
      }
    };

    const statsInterval = setInterval(fetchStats, 1000);
    fetchStats();
    return () => clearInterval(statsInterval);
  }, [setTelemetry]);

  return (
    <div className="panel hud-panel">
      <h2 className="hud-title">Three-Headed Semantic Firewall</h2>
      <p className="hud-subtitle">Geometric prompt gate · local-first</p>

      {/* --- Three Monkey Heads --- */}
      <div className="monkey-row">
        <MonkeyHead alive={noiseEnabled} label="NOISE" frameIdx={frameIdx} />
        <MonkeyHead alive={cosineEnabled} label="COSINE" frameIdx={frameIdx + 1} />
        <MonkeyHead alive={excitationEnabled} label="EXCITE" frameIdx={frameIdx + 2} />
      </div>

      {/* --- System State --- */}
      <div className="system-state">
        <span className="sys-prefix">[SYS] </span>
        <span className="sys-value">{systemAction}</span>
      </div>

      {/* --- Compact Telemetry Line --- */}
      <div className="telemetry-line">
        <span>CPU {telemetry.cpu.toFixed(0)}%</span>
        <span>RAM {telemetry.ram.toFixed(0)}MB</span>
        <span>GPU {telemetry.gpu.toFixed(0)}%</span>
      </div>
    </div>
  );
};
