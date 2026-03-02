import { useEffect, useState } from 'react';
import { EXPORTER_METRICS_ENDPOINT } from '../config/exporterConfig';

type Health = 'Online' | 'Offline' | 'Unknown';

// Enhanced health check with simple thresholds and retry hints
export function useExporterHealth(pingUrl?: string, intervalMs: number = 5000): Health {
  const url = pingUrl?.trim() ? pingUrl.trim() : EXPORTER_METRICS_ENDPOINT;
  const [status, setStatus] = useState<Health>('Unknown');
  const [lastOk, setLastOk] = useState<number | null>(null);

  useEffect(() => {
    let mounted = true;
    const probe = async () => {
      try {
        const res = await fetch(url, { cache: 'no-store' as RequestCache });
        if (!mounted) return;
        if (res.ok) {
          setStatus('Online');
          setLastOk(Date.now());
        } else {
          // degraded if we can still reach the endpoint but returns error
          const sinceOk = lastOk ? Date.now() - lastOk : Infinity;
          setStatus(sinceOk < 60000 ? 'Degraded' : 'Offline');
        }
      } catch {
        const sinceOk = lastOk ? Date.now() - lastOk : Infinity;
        if (!mounted) return;
        setStatus(sinceOk < 60000 ? 'Degraded' : 'Offline');
      }
    };
    probe();
    const id = setInterval(probe, intervalMs);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [url, intervalMs, lastOk]);

  return status;
}

export default useExporterHealth;
