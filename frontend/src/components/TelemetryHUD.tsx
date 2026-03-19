import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import { API_BASE_URL } from '../config';

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
    <div style={{
      textAlign: 'center',
      opacity: alive ? 1 : 0.25,
      transition: 'opacity 0.3s',
      minWidth: '4.5rem',
    }}>
      <pre style={{
        margin: 0,
        fontFamily: 'monospace',
        fontSize: '9px',
        lineHeight: '10px',
        color: alive ? 'var(--accent)' : '#555',
      }}>
        {lines.join('\n')}
      </pre>
      <div style={{
        fontSize: '0.55rem',
        marginTop: '2px',
        color: alive ? 'var(--accent)' : '#444',
        letterSpacing: '0.5px',
        fontWeight: 'bold',
      }}>
        {label}
      </div>
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
    <div className="panel" style={{ paddingBottom: '0.6rem' }}>
      <h2 style={{ fontSize: '1rem', marginBottom: '0.4rem', paddingBottom: '0.3rem' }}>Three-headed Semantic Firewall</h2>

      {/* --- Three Monkey Heads --- */}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', gap: '0.3rem', margin: '0.3rem 0' }}>
        <MonkeyHead alive={noiseEnabled} label="NOISE" frameIdx={frameIdx} />
        <MonkeyHead alive={cosineEnabled} label="COSINE" frameIdx={frameIdx + 1} />
        <MonkeyHead alive={excitationEnabled} label="EXCITE" frameIdx={frameIdx + 2} />
      </div>

      {/* --- System State --- */}
      <div style={{ fontFamily: 'monospace', fontSize: '0.7rem', textAlign: 'center', margin: '0.3rem 0' }}>
        <span style={{ opacity: 0.4 }}>[SYS] </span>
        <span style={{ color: 'var(--accent)' }}>{systemAction}</span>
      </div>

      {/* --- Compact Telemetry Line --- */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: '1rem',
        fontFamily: 'monospace',
        fontSize: '0.6rem',
        opacity: 0.5,
        borderTop: '1px solid #222',
        paddingTop: '0.3rem',
        marginTop: '0.2rem',
      }}>
        <span>CPU {telemetry.cpu.toFixed(0)}%</span>
        <span>RAM {telemetry.ram.toFixed(0)}MB</span>
        <span>GPU {telemetry.gpu.toFixed(0)}%</span>
      </div>
    </div>
  );
};
