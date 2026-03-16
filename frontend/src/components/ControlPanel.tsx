import React, { useRef, useState, useEffect } from 'react';
import { useStore } from '../store';

export const ControlPanel: React.FC = () => {
  const {
    excitationThreshold,
    noiseTolerance,
    cosineThreshold,
    setExcitationThreshold,
    setNoiseTolerance,
    setCosineThreshold,
    ingestionStatus,
    setIngestionStatus,
    setSystemAction
  } = useStore();

  const [packs, setPacks] = useState<{ filename: string, chunks: number }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchPacks = async () => {
    try {
      const res = await fetch('http://localhost:8000/corpus/packs');
      const data = await res.json();
      setPacks(data.packs || []);
    } catch (err) {
      console.error("Failed to fetch packs:", err);
    }
  };

  useEffect(() => {
    fetchPacks();
  }, []);

  // Debounce API calls for config
  useEffect(() => {
    const timer = setTimeout(() => {
      fetch('http://localhost:8000/galaxy/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          excitation_threshold: excitationThreshold,
          noise_tolerance: noiseTolerance,
          cosine_threshold: cosineThreshold
        })
      }).catch(err => console.error("Failed to sync config:", err));
    }, 500);
    return () => clearTimeout(timer);
  }, [excitationThreshold, noiseTolerance, cosineThreshold]);

  // Poll for ingestion status if task is active
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
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
          setSystemAction(`INGESTING_CORPUS: \${Math.round(data.progress)}%`);
          if (data.status === 'completed' || data.status === 'failed') {
            setSystemAction('SYSTEM IDLE');
            fetchPacks();
          }
        } catch (err) {
          console.error("Failed to fetch task status", err);
        }
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    }
  }, [ingestionStatus.taskId, ingestionStatus.status, setIngestionStatus, fetchPacks]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    setSystemAction("UPLOADING_PDF...");

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
      setSystemAction("SYSTEM IDLE");
    }
  };

  const handleDeletePack = async (filename: string) => {
    setSystemAction("DELETING_PACK...");
    try {
      await fetch(`http://localhost:8000/corpus/packs/${filename}`, { method: 'DELETE' });
      fetchPacks();
    } catch (err) {
      console.error("Failed to delete pack", err);
    } finally {
      setSystemAction("SYSTEM IDLE");
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

      <div className="slider-group">
        <label>
          Cosine Gate: {cosineThreshold.toFixed(2)}
          <input
            type="range"
            min="0.50" max="0.99" step="0.01"
            value={cosineThreshold}
            onChange={(e) => setCosineThreshold(Number(e.target.value))}
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
        <button onClick={() => fileInputRef.current?.click()} style={{ width: '100%', marginBottom: '1rem' }}>Upload PDF Corpus</button>

        {packs.length > 0 && (
          <div className="pack-list" style={{ textAlign: 'left', fontSize: '0.85rem' }}>
            <strong>Loaded Packs:</strong>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0' }}>
              {packs.map((p) => (
                <li key={p.filename} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem', padding: '0.25rem', background: '#222' }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '150px' }} title={p.filename}>{p.filename} ({p.chunks} chunks)</span>
                  <button onClick={() => handleDeletePack(p.filename)} style={{ padding: '0.1rem 0.3rem', fontSize: '0.7rem', color: 'var(--danger)', borderColor: 'var(--danger)' }}>X</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {ingestionStatus.taskId && ingestionStatus.status !== 'completed' && (
          <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
            <div>Status: {ingestionStatus.status}</div>
            <div>{ingestionStatus.message}</div>
            <div style={{ width: '100%', background: '#333', height: '4px', marginTop: '4px' }}>
              <div style={{ width: `${ingestionStatus.progress}%`, background: 'var(--accent)', height: '100%' }}></div>
            </div>
          </div>
        )}
      </div>
    </div >
  );
};
