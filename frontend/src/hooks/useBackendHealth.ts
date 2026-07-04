import { useEffect } from 'react';
import { API_BASE_URL } from '../config';
import { useStore } from '../store';

const HEALTH_TIMEOUT_MS = 4000;
const POLL_MS = 3000;

export function useBackendHealth() {
  const setBackendHealth = useStore((s) => s.setBackendHealth);

  useEffect(() => {
    let alive = true;

    const check = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`, {
          signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
        });
        if (!alive) return;
        if (res.ok) {
          setBackendHealth({
            status: 'ok',
            hint: 'Backend responding on port 8000',
            checkedAt: Date.now(),
          });
        } else {
          setBackendHealth({
            status: 'offline',
            hint: `Backend error (HTTP ${res.status}) — check terminal logs`,
            checkedAt: Date.now(),
          });
        }
      } catch {
        if (!alive) return;
        setBackendHealth({
          status: 'offline',
          hint: 'Backend offline — run ./run_server.sh from repo root',
          checkedAt: Date.now(),
        });
      }
    };

    check();
    const id = setInterval(check, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [setBackendHealth]);
}
