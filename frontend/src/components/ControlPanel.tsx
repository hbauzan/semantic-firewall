import React, { useRef, useState, useEffect } from 'react';
import { useStore } from '../store';

export const ControlPanel: React.FC = () => {
    const {
        excitationThreshold,
        noiseTolerance,
        setExcitationThreshold,
        setNoiseTolerance,
        ingestionStatus,
        setIngestionStatus
    } = useStore();

    const [auditQuery, setAuditQuery] = useState('');
    const [auditResult, setAuditResult] = useState<{ activations: number, text: string } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Debounce API calls for config
    useEffect(() => {
        const timer = setTimeout(() => {
            fetch('http://localhost:8000/galaxy/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    excitation_threshold: excitationThreshold,
                    noise_tolerance: noiseTolerance
                })
            }).catch(err => console.error("Failed to sync config:", err));
        }, 500);
        return () => clearTimeout(timer);
    }, [excitationThreshold, noiseTolerance]);

    // Poll for ingestion status if task is active
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (ingestionStatus.taskId && (ingestionStatus.status === 'pending' || ingestionStatus.status === 'processing')) {
            interval = setInterval(async () => {
                try {
                    const res = await fetch(`http://localhost:8000/corpus/task-status/${ingestionStatus.taskId}`);
                    const data = await res.json();
                    setIngestionStatus({
                        status: data.status,
                        progress: data.progress,
                        message: data.message
                    });
                } catch (err) {
                    console.error("Failed to fetch task status", err);
                }
            }, 1000);
        }
        return () => {
            if (interval) clearInterval(interval);
        }
    }, [ingestionStatus.taskId, ingestionStatus.status, setIngestionStatus]);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('http://localhost:8000/corpus/upload-pdf', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            setIngestionStatus({
                taskId: data.task_id,
                status: 'pending',
                progress: 0,
                message: 'Upload started...'
            });
        } catch (err) {
            console.error("Upload failed", err);
        }
    };

    const runAudit = async () => {
        if (!auditQuery.trim()) return;
        try {
            const res = await fetch('http://localhost:8000/audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: auditQuery })
            });
            const data = await res.json();
            setAuditResult(data);
        } catch (err) {
            console.error("Audit failed", err);
        }
    };

    return (
    <div className="panel side-panel" style={{ marginTop: '1rem', width: 'auto' }}>
      <h2>Control Panel</h2>
      
      <div className="slider-group">
        <label>
          Excitation Threshold: {excitationThreshold}
          <input 
            type="range" 
            min="0" max="1024" step="1" 
            value={excitationThreshold}
            onChange={(e) => setExcitationThreshold(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="slider-group">
        <label>
          Noise Tolerance: {noiseTolerance.toFixed(3)}
          <input 
            type="range" 
            min="0.001" max="0.100" step="0.001" 
            value={noiseTolerance}
            onChange={(e) => setNoiseTolerance(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="upload-section">
        <input 
          type="file" 
          accept="application/pdf" 
          ref={fileInputRef}
          onChange={handleFileUpload}
          className="file-input"
        />
        <button onClick={() => fileInputRef.current?.click()}>Upload PDF Corpus</button>
        {ingestionStatus.taskId && (
          <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
            <div>Status: {ingestionStatus.status}</div>
            <div>{ingestionStatus.message}</div>
            <div style={{ width: '100%', background: '#333', height: '4px', marginTop: '4px' }}>
              <div style={{ width: \`\${ingestionStatus.progress}%\`, background: 'var(--accent)', height: '100%' }}></div>
            </div>
          </div>
        )}
      </div>

      <div>
        <h2 style={{ fontSize: '1rem' }}>Stress Test Query</h2>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <input 
            type="text" 
            value={auditQuery}
            onChange={(e) => setAuditQuery(e.target.value)}
            style={{ flexGrow: 1, background: '#000', color: 'var(--text-main)', border: '1px solid var(--border)', padding: '0.5rem' }}
            placeholder="Test query..."
            onKeyDown={(e) => e.key === 'Enter' && runAudit()}
          />
          <button onClick={runAudit}>Audit</button>
        </div>
        {auditResult && (
          <div style={{ background: '#000', padding: '0.5rem', border: '1px solid var(--border)', fontSize: '0.9rem' }}>
            <div><strong>Activations:</strong> {auditResult.activations}</div>
            <div style={{ marginTop: '0.5rem', maxHeight: '100px', overflowY: 'auto' }}>
              <small>{auditResult.text}</small>
            </div>
          </div>
        )}
      </div>
    </div >
  );
};
