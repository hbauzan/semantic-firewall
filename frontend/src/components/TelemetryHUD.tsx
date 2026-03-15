import React, { useEffect, useState } from 'react';
import { useStore } from '../store';

const FRAMES = [
    `
  /\\_/\\
 ( o.o )
  > ^ <
  `,
    `
  /\\_/\\
 ( -.- )
  > ^ <
  `,
    `
  /\\_/\\
 ( o.o )
  > ~ <
  `
];

export const TelemetryHUD: React.FC = () => {
    const { telemetry, setTelemetry } = useStore();
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
            <div className="ascii-art">{FRAMES[frameIdx]}</div>
            <div className="stat-item">
                <span>CPU:</span>
                <span>{telemetry.cpu.toFixed(1)}%</span>
            </div>
            <div className="stat-item">
                <span>RAM:</span>
                <span>{telemetry.ram.toFixed(0)} MB</span>
            </div>
            <div className="stat-item">
                <span>GPU VRAM:</span>
                <span>{telemetry.gpu.toFixed(0)} MB</span>
            </div>
        </div>
    );
};
