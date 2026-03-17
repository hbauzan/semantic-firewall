import React, { useRef, useState, useEffect } from 'react';
import { useStore } from '../store';

// Shared toggle button style generator
const toggleStyle = (on: boolean): React.CSSProperties => ({
  width: '2.2rem', height: '1.3rem', fontSize: '0.55rem', fontWeight: 'bold',
  border: '1px solid', borderColor: on ? 'var(--accent)' : '#555',
  background: on ? 'var(--accent)' : '#222', color: on ? '#000' : '#555',
  cursor: 'pointer', borderRadius: '3px', flexShrink: 0, padding: 0,
});

// Shared Seq input style
const seqInputStyle: React.CSSProperties = {
  width: '2.2rem', textAlign: 'center', background: '#111',
  color: 'var(--accent)', border: '1px solid var(--accent)', padding: '1px', fontSize: '0.7rem',
};

// Step button style
const stepBtnStyle: React.CSSProperties = {
  width: '1.4rem', height: '1.2rem', fontSize: '0.7rem', fontWeight: 'bold',
  padding: 0, border: '1px solid #444', background: '#1a1a1a', color: 'var(--accent)',
  cursor: 'pointer', borderRadius: '2px', flexShrink: 0, lineHeight: 1,
};

// Reusable slider with - / + step buttons
const StepSlider: React.FC<{
  value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; style?: React.CSSProperties;
}> = ({ value, min, max, step, onChange, style }) => {
  const clamp = (v: number) => Math.min(max, Math.max(min, parseFloat(v.toFixed(10))));
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
      <button type="button" style={stepBtnStyle}
        onClick={() => onChange(clamp(value - step))}>-</button>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1, height: '12px', ...style }} />
      <button type="button" style={stepBtnStyle}
        onClick={() => onChange(clamp(value + step))}>+</button>
    </div>
  );
};

export const ControlPanel: React.FC = () => {
  const {
    excitationThreshold, noiseTolerance, cosineThreshold, globalNoiseLimit,
    cosineOrder, excitationOrder, noiseOrder, adaptiveFactor,
    noiseEnabled, cosineEnabled, excitationEnabled,
    setExcitationThreshold, setNoiseTolerance, setCosineThreshold, setGlobalNoiseLimit,
    setCosineOrder, setExcitationOrder, setNoiseOrder, setAdaptiveFactor,
    setNoiseEnabled, setCosineEnabled, setExcitationEnabled,
    ingestionStatus, setIngestionStatus, setSystemAction
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

  useEffect(() => { fetchPacks(); }, []);

  // Debounce API calls for config
  useEffect(() => {
    const timer = setTimeout(() => {
      fetch('http://localhost:8000/galaxy/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          excitation_threshold: excitationThreshold,
          noise_tolerance: noiseTolerance,
          cosine_threshold: cosineThreshold,
          global_noise_limit: globalNoiseLimit,
          cosine_order: cosineOrder,
          excitation_order: excitationOrder,
          noise_order: noiseOrder,
          adaptive_factor: adaptiveFactor,
          noise_enabled: noiseEnabled,
          cosine_enabled: cosineEnabled,
          excitation_enabled: excitationEnabled
        })
      }).catch(err => console.error("Failed to sync config:", err));
    }, 500);
    return () => clearTimeout(timer);
  }, [excitationThreshold, noiseTolerance, cosineThreshold, globalNoiseLimit, cosineOrder, excitationOrder, noiseOrder, adaptiveFactor, noiseEnabled, cosineEnabled, excitationEnabled]);

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
          setSystemAction(`INGESTING_CORPUS: ${Math.round(data.progress)}%`);
          if (data.status === 'completed' || data.status === 'failed') {
            setSystemAction('SYSTEM IDLE');
            fetchPacks();
          }
        } catch (err) {
          console.error("Failed to fetch task status", err);
        }
      }, 1000);
    }
    return () => { if (interval) clearInterval(interval); }
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
      setIngestionStatus({ taskId: data.task_id, status: 'pending', progress: 0, message: 'Upload started...' });
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
    <div className="panel" style={{ width: 'auto', flex: 1, overflow: 'auto' }}>
      <h2 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', paddingBottom: '0.3rem' }}>Control Panel</h2>

      {/* --- Noise Pre-Filter --- */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', opacity: noiseEnabled ? 1 : 0.4, transition: 'opacity 0.2s' }}>
        <button onClick={() => setNoiseEnabled(!noiseEnabled)} style={toggleStyle(noiseEnabled)}>
          {noiseEnabled ? 'ON' : 'OFF'}
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.75rem', marginBottom: '1px' }}>Noise Pre-Filter: <strong>{globalNoiseLimit.toFixed(2)}</strong></div>
          <StepSlider value={globalNoiseLimit} min={0.10} max={2.00} step={0.01} onChange={setGlobalNoiseLimit} />
        </div>
        <div style={{ fontSize: '0.6rem', textAlign: 'center', lineHeight: 1.2 }}>
          <div style={{ opacity: 0.5 }}>Seq</div>
          <input type="number" min="1" max="3" step="1" value={noiseOrder}
            onChange={(e) => setNoiseOrder(Number(e.target.value))} style={seqInputStyle} />
        </div>
      </div>

      {/* --- Cosine Gate --- */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', opacity: cosineEnabled ? 1 : 0.4, transition: 'opacity 0.2s' }}>
        <button onClick={() => setCosineEnabled(!cosineEnabled)} style={toggleStyle(cosineEnabled)}>
          {cosineEnabled ? 'ON' : 'OFF'}
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.75rem', marginBottom: '1px' }}>Cosine Gate: <strong>{cosineThreshold.toFixed(2)}</strong></div>
          <StepSlider value={cosineThreshold} min={0.00} max={1.00} step={0.01} onChange={setCosineThreshold} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', opacity: 0.4, marginTop: '-2px' }}>
            <span>0 LAX</span><span>STRICT 1</span>
          </div>
        </div>
        <div style={{ fontSize: '0.6rem', textAlign: 'center', lineHeight: 1.2 }}>
          <div style={{ opacity: 0.5 }}>Seq</div>
          <input type="number" min="1" max="3" step="1" value={cosineOrder}
            onChange={(e) => setCosineOrder(Number(e.target.value))} style={seqInputStyle} />
        </div>
      </div>

      {/* --- Excitation Filter --- */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', opacity: excitationEnabled ? 1 : 0.4, transition: 'opacity 0.2s' }}>
        <button onClick={() => setExcitationEnabled(!excitationEnabled)} style={toggleStyle(excitationEnabled)}>
          {excitationEnabled ? 'ON' : 'OFF'}
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.75rem', marginBottom: '1px' }}>Excitation: <strong>{excitationThreshold}</strong></div>
          <StepSlider value={excitationThreshold} min={0} max={1024} step={1} onChange={setExcitationThreshold} />
          <div style={{ fontSize: '0.65rem', opacity: 0.5, marginTop: '-1px' }}>
            Noise Tolerance: {noiseTolerance.toFixed(3)}
          </div>
          <StepSlider value={noiseTolerance} min={0.001} max={0.100} step={0.001} onChange={setNoiseTolerance} />
        </div>
        <div style={{ fontSize: '0.6rem', textAlign: 'center', lineHeight: 1.2 }}>
          <div style={{ opacity: 0.5 }}>Seq</div>
          <input type="number" min="1" max="3" step="1" value={excitationOrder}
            onChange={(e) => setExcitationOrder(Number(e.target.value))} style={seqInputStyle} />
        </div>
      </div>

      {/* --- Adaptive Factor --- */}
      <div style={{ marginBottom: '0.5rem', padding: '0.3rem 0', borderTop: '1px solid #222' }}>
        <div style={{ fontSize: '0.75rem', marginBottom: '1px' }}>Adaptive Factor: <strong>{adaptiveFactor.toFixed(2)}</strong></div>
        <StepSlider value={adaptiveFactor} min={0.01} max={1.00} step={0.01} onChange={setAdaptiveFactor} />
        <div style={{ fontSize: '0.6rem', opacity: 0.5, display: 'flex', justifyContent: 'space-between' }}>
          <span>Short: {Math.floor(excitationThreshold * adaptiveFactor)} dims</span>
          <span>Full: {excitationThreshold} dims</span>
        </div>
      </div>

      {/* --- Corpus Upload --- */}
      <div style={{ borderTop: '1px solid #222', paddingTop: '0.4rem' }}>
        <input type="file" accept="application/pdf" ref={fileInputRef}
          onChange={handleFileUpload} className="file-input" />
        <button onClick={() => fileInputRef.current?.click()}
          style={{ width: '100%', padding: '0.35rem', fontSize: '0.75rem', marginBottom: '0.4rem' }}>
          Upload PDF Corpus
        </button>

        {packs.length > 0 && (
          <div style={{ fontSize: '0.75rem' }}>
            <div style={{ opacity: 0.6, marginBottom: '0.2rem' }}>Loaded Packs:</div>
            {packs.map((p) => (
              <div key={p.filename} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '0.15rem 0.3rem', background: '#1a1a1a', marginBottom: '2px', borderRadius: '2px',
              }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '170px', fontSize: '0.7rem' }}
                  title={p.filename}>{p.filename} ({p.chunks})</span>
                <button onClick={() => handleDeletePack(p.filename)}
                  style={{ padding: '0 0.25rem', fontSize: '0.6rem', color: 'var(--danger)', borderColor: 'var(--danger)', lineHeight: 1.4 }}>X</button>
              </div>
            ))}
          </div>
        )}

        {ingestionStatus.taskId && ingestionStatus.status !== 'completed' && (
          <div style={{ marginTop: '0.3rem', fontSize: '0.7rem' }}>
            <span style={{ opacity: 0.6 }}>{ingestionStatus.status}</span> {ingestionStatus.message}
            <div style={{ width: '100%', background: '#333', height: '3px', marginTop: '3px', borderRadius: '2px' }}>
              <div style={{ width: `${ingestionStatus.progress}%`, background: 'var(--accent)', height: '100%', borderRadius: '2px' }}></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
