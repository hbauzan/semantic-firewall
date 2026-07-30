import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useStore } from '../store';
import { API_BASE_URL } from '../config';
import { TOOLTIP_REGISTRY, type TooltipEntry } from '../locales/tooltips';
import { NEGATIVE_RECOMMENDED, POSITIVE_RECOMMENDED, THRESHOLD_SLIDERS } from '../thresholdBounds';
import { useBackendHealth } from '../hooks/useBackendHealth';
import { TaskProgressBar } from './TaskProgressBar';
import { parseApiError } from '../lib/parseApiError';
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

const lang = 'en';

type PackInfo = { filename: string; chunks: number; calibratable?: boolean; has_auto_dataset?: boolean };

const InfoTooltip: React.FC<{ entry: TooltipEntry }> = ({ entry }) => (
  <span className="info-icon">
    i
    <div className="tooltip-box">
      <div style={{ marginBottom: '4px' }}><strong>What is it?</strong> {entry.what}</div>
      <div style={{ marginBottom: '4px' }}><strong>How it works:</strong> {entry.how}</div>
      <div><strong>Suggested:</strong> {entry.suggested}</div>
    </div>
  </span>
);


export const ControlPanel: React.FC = () => {
  const {
    excitationThreshold, noiseTolerance, cosineThreshold, globalNoiseLimit,
    cosineOrder, excitationOrder, noiseOrder, adaptiveFactor,
    noiseEnabled, cosineEnabled, excitationEnabled, ragTopK, firewallMode, activeTab,
    upstreamProvider, snifferViewLimit, calibrationCoverage, lastCalibratedConfig,
    setExcitationThreshold, setNoiseTolerance, setCosineThreshold, setGlobalNoiseLimit,
    setCosineOrder, setExcitationOrder, setNoiseOrder, setAdaptiveFactor,
    setNoiseEnabled, setCosineEnabled, setExcitationEnabled, setRagTopK, setFirewallMode,
    setUpstreamProvider, setSnifferViewLimit, setCalibrationCoverage, setLastCalibratedConfig,
    ingestionStatus, setIngestionStatus, setSystemAction,
    backendHealth, activeTask, startTask, updateTask, finishTask,
  } = useStore();

  useBackendHealth();

  const [packs, setPacks] = useState<PackInfo[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Profile state ---
  const [profiles, setProfiles] = useState<string[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>('');
  const [newProfileName, setNewProfileName] = useState<string>('');
  const [configHydrated, setConfigHydrated] = useState(false);
  const [calibratingPack, setCalibratingPack] = useState<string | null>(null);
  const [calibrationTaskId, setCalibrationTaskId] = useState<string | null>(null);
  const [calibratedThisSession, setCalibratedThisSession] = useState<Set<string>>(() => new Set());
  const [uploadError, setUploadError] = useState<string | null>(null);

  const packWasCalibratedBefore = (pack: PackInfo) =>
    pack.has_auto_dataset === true || calibratedThisSession.has(pack.filename);

  const applyConfigToStore = (c: Record<string, unknown>, updateCalibratedBaseline = true) => {
    setExcitationThreshold(c.excitation_threshold as number);
    setNoiseTolerance(c.noise_tolerance as number);
    setCosineThreshold(c.cosine_threshold as number);
    setGlobalNoiseLimit(c.global_noise_limit as number);
    setCosineOrder(c.cosine_order as number);
    setExcitationOrder(c.excitation_order as number);
    setNoiseOrder(c.noise_order as number);
    setAdaptiveFactor(c.adaptive_factor as number);
    setRagTopK(c.rag_top_k as number);
    setNoiseEnabled(c.noise_enabled as boolean);
    setCosineEnabled(c.cosine_enabled as boolean);
    setExcitationEnabled(c.excitation_enabled as boolean);
    setFirewallMode(c.firewall_mode as 'positive' | 'negative');
    if (c.sniffer_view_limit) setSnifferViewLimit(c.sniffer_view_limit as number);
    if (c.upstream_provider) setUpstreamProvider(c.upstream_provider as typeof upstreamProvider);
    if (c.calibration_coverage) setCalibrationCoverage(c.calibration_coverage as any);

    if (updateCalibratedBaseline && c.cosine_threshold !== undefined && c.excitation_threshold !== undefined && c.global_noise_limit !== undefined) {
      setLastCalibratedConfig({
        cosine_threshold: c.cosine_threshold as number,
        excitation_threshold: c.excitation_threshold as number,
        global_noise_limit: c.global_noise_limit as number,
        noise_tolerance: c.noise_tolerance as number | undefined,
        adaptive_factor: c.adaptive_factor as number | undefined,
      });
    }
  };

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
        applyConfigToStore(c);
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
      applyConfigToStore(c);
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
          sniffer_view_limit: snifferViewLimit,
        })
      }).then(res => {
        if (!res.ok) console.warn(`Config sync failed: ${res.status}`);
      }).catch(err => console.error("Failed to sync config:", err));
    }, 500);
    return () => clearTimeout(timer);
  }, [excitationThreshold, noiseTolerance, cosineThreshold, globalNoiseLimit, cosineOrder, excitationOrder, noiseOrder, adaptiveFactor, noiseEnabled, cosineEnabled, excitationEnabled, ragTopK, firewallMode, activeTab, upstreamProvider, snifferViewLimit, configHydrated]);

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
          const phase = data.message || data.status;
          setIngestionStatus({
            taskId: ingestionStatus.taskId,
            status: data.status,
            progress: data.progress,
            message: data.message
          });
          updateTask({
            phase,
            progress: data.progress,
            stalled: false,
          });
          if (data.status === 'completed') {
            finishTask('success', `INGESTED ${Math.round(data.progress)}%`);
            setUploadError(null);
            setIngestionStatus({ taskId: null, status: 'idle', progress: 0, message: '' });
            fetchPacks();
          } else if (data.status === 'failed') {
            finishTask('error', 'INGESTION_FAILED');
            setUploadError(data.message || 'Ingestion failed');
            setIngestionStatus({ taskId: null, status: 'idle', progress: 0, message: '' });
          }
        } catch (err) {
          console.error("Failed to fetch task status", err);
          updateTask({ phase: 'Waiting for backend task status…', stalled: true });
        }
      }, 1000);
    }
    return () => { if (interval) clearInterval(interval); }
  }, [ingestionStatus.taskId, ingestionStatus.status, setIngestionStatus, updateTask, finishTask, fetchPacks]);

  // Poll calibration task status
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (calibrationTaskId) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/corpus/calibration-task-status/${calibrationTaskId}`);
          if (!res.ok) {
            console.warn(`Calibration status poll: ${res.status}`);
            return;
          }
          const data = await res.json();
          updateTask({
            phase: data.message || data.status,
            progress: data.progress,
            stalled: false,
          });
          if (data.status === 'completed' && data.result) {
            const calibratedFilename = data.result.filename as string;
            applyConfigToStore(data.result.config);
            setCalibratedThisSession((prev) => new Set(prev).add(calibratedFilename));
            const method = data.result.generation_method === 'template_fallback'
              ? ' (template fallback)'
              : '';
            finishTask(
              'success',
              `CALIBRATED ${data.result.corpus_id} (${Math.round(data.result.accuracy * 100)}%)${method}`,
            );
            setCalibrationTaskId(null);
            setCalibratingPack(null);
            setUploadError(null);
            fetchPacks();
          } else if (data.status === 'failed') {
            setUploadError(data.message || 'Calibration failed');
            finishTask('error', 'CALIBRATION_FAILED');
            setCalibrationTaskId(null);
            setCalibratingPack(null);
          }
        } catch (err) {
          console.error('Failed to fetch calibration task status', err);
          updateTask({ phase: 'Waiting for backend calibration status…', stalled: true });
        }
      }, 1000);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [calibrationTaskId, updateTask, finishTask, fetchPacks]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Clear input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    const formData = new FormData();
    formData.append('file', file);
    setUploadError(null);
    startTask({
      kind: 'upload',
      title: 'PDF upload',
      phase: 'Sending file to backend…',
      progress: 0,
    });
    try {
      const res = await fetch(`${API_BASE_URL}/corpus/upload-pdf`, {
        method: 'POST',
        body: formData
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(parseApiError(errText));
      }
      const data = await res.json();
      setIngestionStatus({ taskId: data.task_id, status: 'pending', progress: 0, message: 'Upload started…' });
      updateTask({ phase: 'Queued for ingestion', progress: 0 });
    } catch (err) {
      console.error("Upload failed", err);
      const online = backendHealth.status === 'ok';
      setUploadError(
        online
          ? (err instanceof Error ? err.message : 'Upload failed')
          : 'Backend is not running on port 8000. Start it with: ./run_server.sh'
      );
      finishTask('error', 'UPLOAD_FAILED');
    }
  };

  const handleCalibratePack = async (pack: PackInfo) => {
    const { filename } = pack;

    if (packWasCalibratedBefore(pack)) {
      const ok = window.confirm(
        `"${filename}" was already calibrated.\n\n`
        + 'Re-run the threshold sweep? This takes several minutes and will overwrite the current slider values.',
      );
      if (!ok) return;
    }

    setCalibratingPack(filename);
    setUploadError(null);
    startTask({
      kind: 'calibrate',
      title: `Calibrate ${filename}`,
      phase: 'Extracting corpus sample…',
      progress: 0,
    });

    try {
      const res = await fetch(
        `${API_BASE_URL}/corpus/packs/${encodeURIComponent(filename)}/calibrate-positive?coverage=${calibrationCoverage}`,
        { method: 'POST' },
      );
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(parseApiError(errText));
      }
      const data = await res.json();
      setCalibrationTaskId(data.task_id);
      updateTask({ phase: 'Calibration queued', progress: 0 });
    } catch (err) {
      console.error('Calibration failed', err);
      const msg = err instanceof Error ? err.message : 'Calibration failed';
      setUploadError(msg);
      finishTask('error', 'CALIBRATION_FAILED');
      setCalibratingPack(null);
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

  const handleResetToCalibrated = () => {
    if (lastCalibratedConfig) {
      setCosineThreshold(lastCalibratedConfig.cosine_threshold);
      setExcitationThreshold(lastCalibratedConfig.excitation_threshold);
      setGlobalNoiseLimit(lastCalibratedConfig.global_noise_limit);
      if (lastCalibratedConfig.noise_tolerance !== undefined) {
        setNoiseTolerance(lastCalibratedConfig.noise_tolerance);
      }
      if (lastCalibratedConfig.adaptive_factor !== undefined) {
        setAdaptiveFactor(lastCalibratedConfig.adaptive_factor);
      }
    } else {
      const rec = isNeg ? NEGATIVE_RECOMMENDED : POSITIVE_RECOMMENDED;
      setCosineThreshold(rec.cosine);
      setExcitationThreshold(rec.excitation);
      setGlobalNoiseLimit(rec.globalNoise);
    }
  };

  return (
    <div className="panel" style={{ width: 'auto', flex: 1, overflow: 'auto' }}>
      <h2 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', paddingBottom: '0.3rem' }}>Control Panel</h2>

      {/* --- Upstream Provider Selection --- */}
      <div className="config-section" style={{ marginBottom: '1rem' }}>
        <div className="slider-label">
          Upstream LLM Engine
          <InfoTooltip entry={TOOLTIP_REGISTRY[lang].upstream} />
        </div>
        <select
          value={upstreamProvider}
          onChange={(e) => setUpstreamProvider(e.target.value as any)}
          className="upstream-select"
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
            <InfoTooltip entry={TOOLTIP_REGISTRY[lang].mode} />
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

      {!noiseEnabled && !cosineEnabled && !excitationEnabled && (
        <div className="bypass-warning">
          All filters are OFF — queries bypass the firewall and go straight to the LLM.
        </div>
      )}

      <div className="reset-row">
        <button type="button" onClick={handleResetToCalibrated} className="reset-btn">Reset to Calibrated</button>
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
            <InfoTooltip entry={TOOLTIP_REGISTRY[lang].cosine} />
          </div>
          <StepSlider value={cosineThreshold} min={THRESHOLD_SLIDERS.cosine.min} max={THRESHOLD_SLIDERS.cosine.max} step={THRESHOLD_SLIDERS.cosine.step} onChange={setCosineThreshold} />
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

      {/* --- Noise Pre-Filter --- */}
      <div className={`filter-group ${noiseEnabled ? '' : 'filter-group--disabled'}`}>
        <button onClick={() => setNoiseEnabled(!noiseEnabled)}
          className={`toggle-btn ${noiseEnabled ? 'toggle-btn--on' : ''}`}>
          {noiseEnabled ? 'ON' : 'OFF'}
        </button>
        <div style={{ flex: 1 }}>
          <div className="slider-label">
            Noise Pre-Filter (Entropy): <strong>{globalNoiseLimit.toFixed(2)}</strong>
            <InfoTooltip entry={TOOLTIP_REGISTRY[lang].noise} />
          </div>
          <StepSlider value={globalNoiseLimit} min={THRESHOLD_SLIDERS.globalNoise.min} max={THRESHOLD_SLIDERS.globalNoise.max} step={THRESHOLD_SLIDERS.globalNoise.step} onChange={setGlobalNoiseLimit} />
        </div>
        <div className="seq-column">
          <div className="seq-label">Seq</div>
          <input type="number" min="1" max="3" step="1" value={noiseOrder}
            onChange={(e) => handleOrderChange('noise', Number(e.target.value))} className="seq-input" />
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
            <InfoTooltip entry={TOOLTIP_REGISTRY[lang].excitation} />
          </div>
          <StepSlider value={excitationThreshold} min={THRESHOLD_SLIDERS.excitation.min} max={THRESHOLD_SLIDERS.excitation.max} step={THRESHOLD_SLIDERS.excitation.step} onChange={setExcitationThreshold} />
          <div className="noise-tolerance-label">
            Noise Tolerance: {noiseTolerance.toFixed(3)}
            <InfoTooltip entry={TOOLTIP_REGISTRY[lang].tolerance} />
          </div>
          <StepSlider value={noiseTolerance} min={0.001} max={0.100} step={0.001} onChange={setNoiseTolerance} />
        </div>
        <div className="seq-column">
          <div className="seq-label">
            Seq
            <InfoTooltip entry={TOOLTIP_REGISTRY[lang].seq} />
          </div>
          <input type="number" min="1" max="3" step="1" value={excitationOrder}
            onChange={(e) => handleOrderChange('excitation', Number(e.target.value))} className="seq-input" />
        </div>
      </div>

      {/* --- Adaptive Factor --- */}
      <div className="config-section">
        <div className="slider-label">
          Adaptive Factor: <strong>{adaptiveFactor.toFixed(2)}</strong>
          <InfoTooltip entry={TOOLTIP_REGISTRY[lang].adaptive} />
        </div>
        <StepSlider value={adaptiveFactor} min={0.01} max={1.00} step={0.01} onChange={setAdaptiveFactor} />
        <div className="slider-sublabel">
          <span>Short: {Math.floor(excitationThreshold * adaptiveFactor)} dims</span>
          <span>Full: {excitationThreshold} dims</span>
        </div>
      </div>

      {/* --- RAG Top-K --- */}
      <div className="config-section">
        <div className="slider-label">
          RAG Context Depth: <strong>{ragTopK}</strong> chunk{ragTopK > 1 ? 's' : ''}
          <InfoTooltip entry={TOOLTIP_REGISTRY[lang].rag} />
        </div>
        <StepSlider value={ragTopK} min={1} max={32} step={1} onChange={setRagTopK} />
        <div className="slider-sublabel">
          <span>1 (fast)</span>
          <span>10 (deep)</span>
        </div>
      </div>

      {/* --- Config Profiles --- */}
      <div className="profiles-section">
        <div className="section-title">
          Config Profiles
          <InfoTooltip entry={TOOLTIP_REGISTRY[lang].profiles} />
        </div>
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
        <div className="section-title corpus-section-title">
          Document Corpus
          <InfoTooltip entry={TOOLTIP_REGISTRY[lang].corpus} />
        </div>

        <div className="config-section" style={{ marginBottom: '0.8rem' }}>
          <div className="slider-label">
            Calibration Coverage Mode
          </div>
          <select
            value={calibrationCoverage}
            onChange={(e) => setCalibrationCoverage(e.target.value as any)}
            className="upstream-select"
            title="Coverage mode for automatic corpus calibration"
          >
            <option value="fast">Fast (Minimum ~10 queries)</option>
            <option value="recommended">Recommended (Balanced ~30 queries)</option>
            <option value="exhaustive">Exhaustive (Maximum ~100 queries)</option>
          </select>
        </div>

        {packs.length === 0 && !ingestionStatus.taskId && (
          <div className="empty-state-card">
            <p>No corpus loaded. Positive mode needs a PDF to verify queries.</p>
            <p className="empty-state-hint">Upload a PDF below to get started.</p>
          </div>
        )}

        {backendHealth.status === 'offline' && (
          <div className="corpus-alert corpus-alert--offline">
            Backend offline — PDF upload needs the API on port 8000 (`./run_server.sh`).
          </div>
        )}

        {uploadError && (
          <div className="corpus-alert corpus-alert--error" role="alert">
            {uploadError}
          </div>
        )}

        {activeTask && (activeTask.kind === 'upload' || activeTask.kind === 'calibrate') && (
          <div className="corpus-task-status">
            <div className="corpus-task-label">
              <span className="status-label">{activeTask.kind}</span>
              {' '}{activeTask.phase}
              {activeTask.progress !== null ? ` (${Math.round(activeTask.progress)}%)` : ''}
              {activeTask.stalled ? ' — stalled, check backend logs' : ''}
            </div>
            <TaskProgressBar progress={activeTask.progress} stalled={activeTask.stalled} />
          </div>
        )}

        <input type="file" accept="application/pdf" ref={fileInputRef}
          onChange={handleFileUpload} className="file-input" />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="corpus-upload-btn"
          disabled={activeTask?.kind === 'upload' || activeTask?.kind === 'calibrate'}
        >
          Upload PDF Corpus
        </button>

        {packs.length > 0 && (
          <div className="packs-list">
            <div className="packs-title">Loaded Packs:</div>
            {packs.map((p) => (
              <div key={p.filename} className="pack-item">
                <span className="pack-name" title={p.filename}>{p.filename} ({p.chunks})</span>
                <div className="pack-actions">
                  <button
                    type="button"
                    onClick={() => handleCalibratePack(p)}
                    className="pack-calibrate-btn"
                    disabled={calibratingPack !== null || activeTask?.kind === 'upload' || activeTask?.kind === 'calibrate'}
                    title={
                      p.calibratable
                        ? 'Calibrate thresholds (hand-curated dataset)'
                        : p.has_auto_dataset
                          ? 'Calibrate thresholds (cached auto dataset)'
                          : 'Calibrate thresholds (auto-generate dataset)'
                    }
                  >
                    {calibratingPack === p.filename ? '…' : 'Cal'}
                  </button>
                  <button type="button" onClick={() => handleDeletePack(p.filename)} className="pack-delete-btn">X</button>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
};
