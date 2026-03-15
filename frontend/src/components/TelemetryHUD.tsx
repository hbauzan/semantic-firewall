import React, { useEffect, useState } from 'react';
import { useStore } from '../store';

const FRAMES = [
    `
  .---.
 /_____\\
 ( x.o )
  > m <
  `,
    `
  .---.
 /_____\\
 ( x.- )
  > m <
  `,
    `
  .---.
 /_____\\
 ( x.o )
  > O <
  `
];

export const TelemetryHUD: React.FC = () => {
    const { telemetry, setTelemetry, systemAction } = useStore();
    const [frameIdx, setFrameIdx] = useState(0);

    useEffect(() => {
        const animationInterval = setInterval(() => {
            setFrameIdx((prev) => (prev + 1) % FRAMES.length);
        }, 500);
        return () => clearInterval(animationInterval);
    }, []);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await fetch('http://localhost:8000/system/stats');
                const data = await res.json();
                setTelemetry(data);
            } catch (err) {
                console.error("Failed to fetch stats", err);
            }
        };

        const statsInterval = setInterval(fetchStats, 1000);
        fetchStats(); // initial fetch
        return () => clearInterval(statsInterval);
    }, [setTelemetry]);

    return (
        <div className="panel">
            <h2>Telemetry HUD</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                <div className="ascii-art" style={{ marginBottom: 0 }}>{FRAMES[frameIdx]}</div>
                <div style={{ flexGrow: 1, fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-main)' }}>
                    <div style={{ opacity: 0.5, marginBottom: '0.2rem' }}>[SYS_STATE]:</div>
                    <div style={{ color: 'var(--accent)' }}>{systemAction}</div>
                </div>
            </div>
            <div className="stat-item">
                <span>CPU:</span>
                <span>{telemetry.cpu.toFixed(1)}%</span>
            </div>
            <div className="stat-item">
                <span>RAM:</span>
                <span>{telemetry.ram.toFixed(0)} MB</span>
            </div>
            <div className="stat-item">
                <span>GPU %:</span>
                <span>{telemetry.gpu.toFixed(1)}%</span>
            </div>
        </div>
    );
};
