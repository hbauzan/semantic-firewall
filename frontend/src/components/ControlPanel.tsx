import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useStore } from '../store';
import { API_BASE_URL } from '../config';

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
    noiseEnabled, cosineEnabled, excitationEnabled, ragTopK, firewallMode, activeTab,
    setExcitationThreshold, setNoiseTolerance, setCosineThreshold, setGlobalNoiseLimit,
    setCosineOrder, setExcitationOrder, setNoiseOrder, setAdaptiveFactor,
    setNoiseEnabled, setCosineEnabled, setExcitationEnabled, setRagTopK, setFirewallMode,
    ingestionStatus, setIngestionStatus, setSystemAction
  } = useStore();

  const [packs, setPacks] = useState<{ filename: string, chunks: number }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Profile state ---
  const [profiles, setProfiles] = useState<string[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>('');
  const [newProfileName, setNewProfileName] = useState<string>('');

  const fetchPacks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/corpus/packs`);
      if (!res.ok) {
        console.warn(`fetchPacks: server returned ${res.status}`);
        return;
      }
      const data = await res.json();
      setPacks(data.packs || []);
    } catch (err) {
      console.error("Failed to fetch packs:", err);
    }
  }, []);

  const fetchProfiles = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/galaxy/profiles`);
      if (!res.ok) return;
      const data = await res.json();
      setProfiles(data.profiles || []);
    } catch (err) {
      console.error("Failed to fetch profiles:", err);
    }
  }, []);

  useEffect(() => { fetchPacks(); fetchProfiles(); }, [fetchPacks, fetchProfiles]);

  const handleSaveProfile = async () => {
    const name = newProfileName.trim();
    if (!name) return;
    try {
      const res = await fetch(`${API_BASE_URL}/galaxy/profiles/save/${encodeURIComponent(name)}`, { method: 'POST' });
      if (!res.ok) { console.warn(`Save profile failed: ${res.status}`); return; }
      setNewProfileName('');
      await fetchProfiles();
    } catch (err) {
      console.error("Failed to save profile:", err);
    }
  };

  const handleLoadProfile = async () => {
    if (!selectedProfile) return;
    try {
      const res = await fetch(`${API_BASE_URL}/galaxy/profiles/load/${encodeURIComponent(selectedProfile)}`, { method: 'POST' });
      if (!res.ok) { console.warn(`Load profile failed: ${res.status}`); return; }
      // Reload the page so Zustand store re-syncs from backend
      window.location.reload();
    } catch (err) {
      console.error("Failed to load profile:", err);
    }
  };

  const handleDeleteProfile = async () => {
    if (!selectedProfile) return;
    try {
      const res = await fetch(`${API_BASE_URL}/galaxy/profiles/${encodeURIComponent(selectedProfile)}`, { method: 'DELETE' });
      if (!res.ok) { console.warn(`Delete profile failed: ${res.status}`); return; }
      setSelectedProfile('');
      await fetchProfiles();
    } catch (err) {
      console.error("Failed to delete profile:", err);
    }
  };

  // Debounce API calls for config
  useEffect(() => {
    const timer = setTimeout(() => {
      fetch(`${API_BASE_URL}/galaxy/config`, {
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
          excitation_enabled: excitationEnabled,
          rag_top_k: ragTopK,
          firewall_mode: firewallMode,
          active_tab: activeTab,
        })
      }).then(res => {
        if (!res.ok) console.warn(`Config sync failed: ${res.status}`);
      }).catch(err => console.error("Failed to sync config:", err));
    }, 500);
    return () => clearTimeout(timer);
  }, [excitationThreshold, noiseTolerance, cosineThreshold, globalNoiseLimit, cosineOrder, excitationOrder, noiseOrder, adaptiveFactor, noiseEnabled, cosineEnabled, excitationEnabled, ragTopK, firewallMode, activeTab]);

  // Poll for ingestion status if task is active
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (ingestionStatus.taskId && (ingestionStatus.status === 'pending' || ingestionStatus.status === 'processing')) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/corpus/task-status/${ingestionStatus.taskId}`);
          if (!res.ok) {
            console.warn(`Task status poll: ${res.status}`);
            return;
          }
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
  }, [ingestionStatus.taskId, ingestionStatus.status, setIngestionStatus, setSystemAction, fetchPacks]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setSystemAction("UPLOADING_PDF...");
    try {
      const res = await fetch(`${API_BASE_URL}/corpus/upload-pdf`, {
        method: 'POST',
        body: formData
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Upload failed (${res.status}): ${errText}`);
      }
      const data = await res.json();
      setIngestionStatus({ taskId: data.task_id, status: 'pending', progress: 0, message: 'Upload started...' });
    } catch (err) {
      console.error("Upload failed", err);
      setSystemAction("UPLOAD_FAILED");
      setTimeout(() => setSystemAction("SYSTEM IDLE"), 3000);
    }
  };

  const handleDeletePack = async (filename: string) => {
    setSystemAction("DELETING_PACK...");
    try {
      const res = await fetch(`${API_BASE_URL}/corpus/packs/${filename}`, { method: 'DELETE' });
      if (!res.ok) console.warn(`Delete pack failed: ${res.status}`);
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

      {/* --- Firewall Mode Toggle --- */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '0.6rem', padding: '0.35rem 0.5rem',
        background: firewallMode === 'negative' ? 'rgba(255, 60, 60, 0.12)' : 'rgba(0, 255, 136, 0.08)',
        border: `1px solid ${firewallMode === 'negative' ? '#ff3c3c' : 'var(--accent)'}`,
        borderRadius: '4px', transition: 'all 0.2s',
      }}>
        <div style={{ fontSize: '0.7rem', lineHeight: 1.3 }}>
          <div style={{ fontWeight: 'bold', color: firewallMode === 'negative' ? '#ff3c3c' : 'var(--accent)' }}>
            {firewallMode === 'positive' ? 'POSITIVE — Allowlist' : 'NEGATIVE — Denylist'}
          </div>
          <div style={{ opacity: 0.6, fontSize: '0.6rem' }}>
            {firewallMode === 'positive' ? 'Only corpus topics pass' : 'Corpus topics are blocked'}
          </div>
        </div>
        <button
          onClick={() => setFirewallMode(firewallMode === 'positive' ? 'negative' : 'positive')}
          style={{
            width: '3.2rem', height: '1.5rem', fontSize: '0.6rem', fontWeight: 'bold',
            border: '1px solid', cursor: 'pointer', borderRadius: '3px', padding: 0,
            borderColor: firewallMode === 'negative' ? '#ff3c3c' : 'var(--accent)',
            background: firewallMode === 'negative' ? '#ff3c3c' : 'var(--accent)',
            color: '#000', transition: 'all 0.2s',
          }}
        >
          {firewallMode === 'positive' ? 'POS' : 'NEG'}
        </button>
      </div>

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

      {/* --- RAG Top-K --- */}
      <div style={{ marginBottom: '0.5rem', padding: '0.3rem 0', borderTop: '1px solid #222' }}>
        <div style={{ fontSize: '0.75rem', marginBottom: '1px' }}>RAG Context Depth: <strong>{ragTopK}</strong> chunk{ragTopK > 1 ? 's' : ''}</div>
        <StepSlider value={ragTopK} min={1} max={10} step={1} onChange={setRagTopK} />
        <div style={{ fontSize: '0.6rem', opacity: 0.5, display: 'flex', justifyContent: 'space-between' }}>
          <span>1 (fast)</span>
          <span>10 (deep)</span>
        </div>
      </div>

      {/* --- Config Profiles --- */}
      <div style={{ borderTop: '1px solid #222', paddingTop: '0.4rem', marginBottom: '0.4rem' }}>
        <div style={{ fontSize: '0.7rem', opacity: 0.6, marginBottom: '0.3rem' }}>Config Profiles</div>
        <div style={{ display: 'flex', gap: '4px', marginBottom: '0.3rem' }}>
          <select
            value={selectedProfile}
            onChange={(e) => setSelectedProfile(e.target.value)}
            style={{
              flex: 1, background: '#111', color: 'var(--accent)', border: '1px solid #444',
              fontSize: '0.7rem', padding: '2px 4px', borderRadius: '2px',
            }}
          >
            <option value="">— select profile —</option>
            {profiles.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <button
            onClick={handleLoadProfile}
            disabled={!selectedProfile}
            style={{ fontSize: '0.65rem', padding: '2px 6px', opacity: selectedProfile ? 1 : 0.4 }}
            title="Load selected profile"
          >LOAD</button>
          <button
            onClick={handleDeleteProfile}
            disabled={!selectedProfile}
            style={{ fontSize: '0.65rem', padding: '2px 6px', color: 'var(--danger)', borderColor: 'var(--danger)', opacity: selectedProfile ? 1 : 0.4 }}
            title="Delete selected profile"
          >DEL</button>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <input
            type="text"
            placeholder="profile name..."
            value={newProfileName}
            onChange={(e) => setNewProfileName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSaveProfile(); }}
            style={{
              flex: 1, background: '#111', color: 'var(--accent)', border: '1px solid #444',
              fontSize: '0.7rem', padding: '2px 4px', borderRadius: '2px',
            }}
          />
          <button
            onClick={handleSaveProfile}
            disabled={!newProfileName.trim()}
            style={{ fontSize: '0.65rem', padding: '2px 6px', opacity: newProfileName.trim() ? 1 : 0.4 }}
            title="Save current config as new profile"
          >SAVE</button>
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
