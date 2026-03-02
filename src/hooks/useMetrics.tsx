import { useEffect, useState } from 'react';
import { MetricsState } from '../types/metrics';
import { EXPORTER_METRICS_ENDPOINT } from '../config/exporterConfig';
import fetchMetrics from '../services/exporter';

// Custom hook to fetch/exporter metrics periodically
export function useMetrics(url?: string, intervalMs: number = 5000) {
  const [data, setData] = useState<MetricsState>({ cpu: [], memory: [], disk: [], network: [] });

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const endpoint = url ?? EXPORTER_METRICS_ENDPOINT;
        const d = await fetchMetrics(endpoint);
        if (mounted) setData(d);
      } catch {
        // keep previous data on error
      }
    };
    load();
    const id = setInterval(load, intervalMs);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [url, intervalMs]);

  // Normalize to chart-friendly Point[]
  const toPoints = (arr: { t: number; v: number }[]) => arr.map((p, i) => ({ x: i, y: p.v }));

  const extrasRaw: any[] = (data as any).extras ?? [];
  const extras = extrasRaw.map((ex) => ({
    name: ex.name,
    data: (ex.data ?? []).map((d: any, i: number) => ({ x: i, y: d.v })),
  }));

  return {
    cpu: data.cpu ? toPoints(data.cpu) : [],
    memory: data.memory ? toPoints(data.memory) : [],
    disk: data.disk ? toPoints(data.disk) : [],
    network: data.network ? toPoints(data.network) : [],
    extras,
  };
}

export default useMetrics;
