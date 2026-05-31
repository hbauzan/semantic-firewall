import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useStore } from '../store';
import { API_BASE_URL } from '../config';
import '../styles/ControlPanel.css';

// Reusable slider with - / + step buttons
const StepSlider: React.FC<{
  value: number; min: number; max: number; step: number;
  onChange: (v: number) => void;
}> = ({ value, min, max, step, onChange }) => {
  const clamp = (v: number) => Math.min(max, Math.max(min, parseFloat(v.toFixed(10))));
  return (
    <div className="slider-row">
      <button type="button" className="step-btn"
        onClick={() => onChange(clamp(value - step))}>-</button>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))} />
      <button type="button" className="step-btn"
        onClick={() => onChange(clamp(value + step))}>+</button>
    </div>
  );
};

// Tooltip Content Mapping
const TOOLTIPS = {
  noise: "Filters repetitive character attacks (GCG). Suggested: 4.5 (Entropy). Lower = more permissive.",
  cosine: "Semantic similarity gate. Suggested: 0.53 (Pos) / 0.62 (Neg). Higher = stricter.",
  excitation: "Exact dimensional resonance. Suggested: 150. Higher = requires near-total alignment."
};


export const ControlPanel: React.FC = () => {
  const {
    excitationThreshold, noiseTolerance, cosineThreshold, globalNoiseLimit,
    cosineOrder, excitationOrder, noiseOrder, adaptiveFactor,
    noiseEnabled, cosineEnabled, excitationEnabled, ragTopK, firewallMode, activeTab,
    upstreamProvider,
    setExcitationThreshold, setNoiseTolerance, setCosineThreshold, setGlobalNoiseLimit,
    setCosineOrder, setExcitationOrder, setNoiseOrder, setAdaptiveFactor,
    setNoiseEnabled, setCosineEnabled, setExcitationEnabled, setRagTopK, setFirewallMode,
    setUpstreamProvider,
    ingestionStatus, setIngestionStatus, setSystemAction
  } = useStore();

  const [packs, setPacks] = useState<{ filename: string, chunks: number }[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Profile state ---
  const [profiles, setProfiles] = useState<string[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>('');
  const [newProfileName, setNewProfileName] = useState<string>('');
  const [configHydrated, setConfigHydrated] = useState(false);

  const handleOrderChange = (filterName: 'noise' | 'cosine' | 'excitation', newOrder: number) => {
    const currentOrders = {
      noise: noiseOrder,
      cosine: cosineOrder,
      excitation: excitationOrder
    };
    
    // Find which filter currently has the target order
    const conflictFilter = Object.keys(currentOrders).find(
      key => currentOrders[key as keyof typeof currentOrders] === newOrder
    ) as keyof typeof currentOrders;

    if (conflictFilter && conflictFilter !== filterName) {
      // Perform the swap: Assign the old order of the current filter to the conflicting one
      const oldOrder = currentOrders[filterName];
      if (conflictFilter === 'noise') setNoiseOrder(oldOrder);
      if (conflictFilter === 'cosine') setCosineOrder(oldOrder);
      if (conflictFilter === 'excitation') setExcitationOrder(oldOrder);
    }
    
    // Set the new order for the target filter
    if (filterName === 'noise') setNoiseOrder(newOrder);
    if (filterName === 'cosine') setCosineOrder(newOrder);
    if (filterName === 'excitation') setExcitationOrder(newOrder);
  };


  // --- Config Hydration from Backend (Finding Q4/F5) ---
  useEffect(() => {
    fetch(`${API_BASE_URL}/galaxy/config`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        const c = data.config;
        setExcitationThreshold(c.excitation_threshold);
        setNoiseTolerance(c.noise_tolerance);
        setCosineThreshold(c.cosine_threshold);
        setGlobalNoiseLimit(c.global_noise_limit);
        setCosineOrder(c.cosine_order);
        setExcitationOrder(c.excitation_order);
        setNoiseOrder(c.noise_order);
        setAdaptiveFactor(c.adaptive_factor);
        setRagTopK(c.rag_top_k);
        setNoiseEnabled(c.noise_enabled);
        setCosineEnabled(c.cosine_enabled);
        setExcitationEnabled(c.excitation_enabled);
        setFirewallMode(c.firewall_mode);
        if (c.upstream_provider) setUpstreamProvider(c.upstream_provider);
        setConfigHydrated(true);
      })
      .catch(err => {
        console.error("Failed to hydrate config from backend:", err);
        setConfigHydrated(true); // proceed with defaults
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
      const data = await res.json();
      // Hydrate store from profile response instead of full page reload (Finding F6)
      const c = data.config;
      setExcitationThreshold(c.excitation_threshold);
      setNoiseTolerance(c.noise_tolerance);
      setCosineThreshold(c.cosine_threshold);
      setGlobalNoiseLimit(c.global_noise_limit);
      setCosineOrder(c.cosine_order);
      setExcitationOrder(c.excitation_order);
      setNoiseOrder(c.noise_order);
      setAdaptiveFactor(c.adaptive_factor);
      setRagTopK(c.rag_top_k);
      setNoiseEnabled(c.noise_enabled);
      setCosineEnabled(c.cosine_enabled);
      setExcitationEnabled(c.excitation_enabled);
      setFirewallMode(c.firewall_mode);
      if (c.upstream_provider) setUpstreamProvider(c.upstream_provider);
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

  // Debounce API calls for config (only after initial hydration)
  useEffect(() => {
    if (!configHydrated) return;
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
          upstream_provider: upstreamProvider,
        })
      }).then(res => {
        if (!res.ok) console.warn(`Config sync failed: ${res.status}`);
      }).catch(err => console.error("Failed to sync config:", err));
    }, 500);
    return () => clearTimeout(timer);
  }, [excitationThreshold, noiseTolerance, cosineThreshold, globalNoiseLimit, cosineOrder, excitationOrder, noiseOrder, adaptiveFactor, noiseEnabled, cosineEnabled, excitationEnabled, ragTopK, firewallMode, activeTab, upstreamProvider, configHydrated]);

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
    
    // Clear input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

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

  const isNeg = firewallMode === 'negative';

  const handleResetToRecommended = () => {
    if (firewallMode === 'positive') {
      setCosineThreshold(0.5315);
      setExcitationThreshold(150);
      setGlobalNoiseLimit(4.5);
    } else {
      setCosineThreshold(0.6197);
      setExcitationThreshold(170);
      setGlobalNoiseLimit(4.5);
    }
  };

  return (
    <div className="panel" style={{ width: 'auto', flex: 1, overflow: 'auto' }}>
      <h2 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', paddingBottom: '0.3rem' }}>Control Panel</h2>

      {/* --- Upstream Provider Selection --- */}
      <div className="config-section" style={{ marginBottom: '1rem' }}>
        <div className="slider-label">Upstream LLM Engine</div>
        <select
          value={upstreamProvider}
          onChange={(e) => setUpstreamProvider(e.target.value as any)}
          style={{ width: '100%', padding: '0.4rem', marginTop: '0.3rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-dark)', color: 'var(--text-primary)' }}
        >
          <option value="ollama">Ollama (Local)</option>
          <option value="google">Google Gemini</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="groq">Groq</option>
        </select>
      </div>

      {/* --- Firewall Mode Toggle --- */}
      <div className={`firewall-mode-banner ${isNeg ? 'firewall-mode-banner--negative' : ''}`}>
        <div className="mode-info">
          <div className="mode-title">
            {isNeg ? 'NEGATIVE \u2014 Denylist' : 'POSITIVE \u2014 Allowlist'}
          </div>
          <div className="mode-subtitle">
            {isNeg ? 'Corpus topics are blocked' : 'Only corpus topics pass'}
          </div>
        </div>
        <button
          onClick={() => setFirewallMode(isNeg ? 'positive' : 'negative')}
          className={`firewall-mode-toggle ${isNeg ? 'firewall-mode-toggle--negative' : ''}`}
        >
          {isNeg ? 'NEG' : 'POS'}
        </button>
      </div>

      <div style={{ marginBottom: '1rem', textAlign: 'center' }}>
        <button onClick={handleResetToRecommended} className="reset-btn" style={{ padding: '0.4rem 1rem', cursor: 'pointer', borderRadius: '4px', backgroundColor: 'var(--bg-light)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>Reset to Recommended</button>
      </div>

      {/* --- Noise Pre-Filter --- */}
      <div className={`filter-group ${noiseEnabled ? '' : 'filter-group--disabled'}`}>
        <button onClick={() => setNoiseEnabled(!noiseEnabled)}
          className={`toggle-btn ${noiseEnabled ? 'toggle-btn--on' : ''}`}>
          {noiseEnabled ? 'ON' : 'OFF'}
        </button>
        <div style={{ flex: 1 }}>
          <div className="slider-label">
            Noise Pre-Filter: <strong>{globalNoiseLimit.toFixed(2)}</strong>
            <span className="info-icon" title={TOOLTIPS.noise} style={{ cursor: 'help', marginLeft: '5px' }}>ⓘ</span>
          </div>
          <StepSlider value={globalNoiseLimit} min={0.10} max={2.00} step={0.01} onChange={setGlobalNoiseLimit} />
        </div>
        <div className="seq-column">
          <div className="seq-label">Seq</div>
          <input type="number" min="1" max="3" step="1" value={noiseOrder}
            onChange={(e) => handleOrderChange('noise', Number(e.target.value))} className="seq-input" />
        </div>
      </div>

      {/* --- Cosine Gate --- */}
      <div className={`filter-group ${cosineEnabled ? '' : 'filter-group--disabled'}`}>
        <button onClick={() => setCosineEnabled(!cosineEnabled)}
          className={`toggle-btn ${cosineEnabled ? 'toggle-btn--on' : ''}`}>
          {cosineEnabled ? 'ON' : 'OFF'}
        </button>
        <div style={{ flex: 1 }}>
          <div className="slider-label">
            Cosine Gate: <strong>{cosineThreshold.toFixed(2)}</strong>
            <span className="info-icon" title={TOOLTIPS.cosine} style={{ cursor: 'help', marginLeft: '5px' }}>ⓘ</span>
          </div>
          <StepSlider value={cosineThreshold} min={0.00} max={1.00} step={0.01} onChange={setCosineThreshold} />
          <div className="slider-hint">
            <span>0 LAX</span><span>STRICT 1</span>
          </div>
        </div>
        <div className="seq-column">
          <div className="seq-label">Seq</div>
          <input type="number" min="1" max="3" step="1" value={cosineOrder}
            onChange={(e) => handleOrderChange('cosine', Number(e.target.value))} className="seq-input" />
        </div>
      </div>

      {/* --- Excitation Filter --- */}
      <div className={`filter-group ${excitationEnabled ? '' : 'filter-group--disabled'}`}>
        <button onClick={() => setExcitationEnabled(!excitationEnabled)}
          className={`toggle-btn ${excitationEnabled ? 'toggle-btn--on' : ''}`}>
          {excitationEnabled ? 'ON' : 'OFF'}
        </button>
        <div style={{ flex: 1 }}>
          <div className="slider-label">
            Excitation: <strong>{excitationThreshold}</strong>
            <span className="info-icon" title={TOOLTIPS.excitation} style={{ cursor: 'help', marginLeft: '5px' }}>ⓘ</span>
          </div>
          <StepSlider value={excitationThreshold} min={0} max={1024} step={1} onChange={setExcitationThreshold} />
          <div className="noise-tolerance-label">
            Noise Tolerance: {noiseTolerance.toFixed(3)}
          </div>
          <StepSlider value={noiseTolerance} min={0.001} max={0.100} step={0.001} onChange={setNoiseTolerance} />
        </div>
        <div className="seq-column">
          <div className="seq-label">Seq</div>
          <input type="number" min="1" max="3" step="1" value={excitationOrder}
            onChange={(e) => handleOrderChange('excitation', Number(e.target.value))} className="seq-input" />
        </div>
      </div>

      {/* --- Adaptive Factor --- */}
      <div className="config-section">
        <div className="slider-label">Adaptive Factor: <strong>{adaptiveFactor.toFixed(2)}</strong></div>
        <StepSlider value={adaptiveFactor} min={0.01} max={1.00} step={0.01} onChange={setAdaptiveFactor} />
        <div className="slider-sublabel">
          <span>Short: {Math.floor(excitationThreshold * adaptiveFactor)} dims</span>
          <span>Full: {excitationThreshold} dims</span>
        </div>
      </div>

      {/* --- RAG Top-K --- */}
      <div className="config-section">
        <div className="slider-label">RAG Context Depth: <strong>{ragTopK}</strong> chunk{ragTopK > 1 ? 's' : ''}</div>
        <StepSlider value={ragTopK} min={1} max={10} step={1} onChange={setRagTopK} />
        <div className="slider-sublabel">
          <span>1 (fast)</span>
          <span>10 (deep)</span>
        </div>
      </div>

      {/* --- Config Profiles --- */}
      <div className="profiles-section">
        <div className="section-title">Config Profiles</div>
        <div className="profiles-row">
          <select
            value={selectedProfile}
            onChange={(e) => setSelectedProfile(e.target.value)}
            className="profile-select"
          >
            <option value="">&mdash; select profile &mdash;</option>
            {profiles.map(p => (
              <option key={p} value={p}>{p === '_last_used' ? '🕒 Last Session (Auto-save)' : p}</option>
            ))}
          </select>
          <button
            onClick={handleLoadProfile}
            disabled={!selectedProfile}
            className={`profile-btn ${!selectedProfile ? 'profile-btn--disabled' : ''}`}
            title="Load selected profile"
          >LOAD</button>
          <button
            onClick={handleDeleteProfile}
            disabled={!selectedProfile}
            className={`profile-btn profile-btn--danger ${!selectedProfile ? 'profile-btn--disabled' : ''}`}
            title="Delete selected profile"
          >DEL</button>
        </div>
        <div className="profiles-row">
          <input
            type="text"
            placeholder="profile name..."
            value={newProfileName}
            onChange={(e) => setNewProfileName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSaveProfile(); }}
            className="profile-input"
          />
          <button
            onClick={handleSaveProfile}
            disabled={!newProfileName.trim()}
            className={`profile-btn ${!newProfileName.trim() ? 'profile-btn--disabled' : ''}`}
            title="Save current config as new profile"
          >SAVE</button>
        </div>
      </div>

      {/* --- Corpus Upload --- */}
      <div className="corpus-section">
        <input type="file" accept="application/pdf" ref={fileInputRef}
          onChange={handleFileUpload} className="file-input" />
        <button onClick={() => fileInputRef.current?.click()} className="corpus-upload-btn">
          Upload PDF Corpus
        </button>

        {packs.length > 0 && (
          <div className="packs-list">
            <div className="packs-title">Loaded Packs:</div>
            {packs.map((p) => (
              <div key={p.filename} className="pack-item">
                <span className="pack-name" title={p.filename}>{p.filename} ({p.chunks})</span>
                <button onClick={() => handleDeletePack(p.filename)} className="pack-delete-btn">X</button>
              </div>
            ))}
          </div>
        )}

        {ingestionStatus.taskId && ingestionStatus.status !== 'completed' && (
          <div className="ingestion-status">
            <span className="status-label">{ingestionStatus.status}</span> {ingestionStatus.message}
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${ingestionStatus.progress}%` }}></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
