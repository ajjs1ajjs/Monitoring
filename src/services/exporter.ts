import { MetricsState } from '../types/metrics';

const DEFAULT_ENDPOINT = '/api/exporter/metrics';

export async function fetchMetrics(url: string = DEFAULT_ENDPOINT): Promise<MetricsState> {
  try {
    const res = await fetch(url, { cache: 'no-store' as RequestCache });
    if (!res.ok) throw new Error('Network response was not ok');
    const data = (await res.json()) as MetricsState;
    // Basic validation
    if (!data?.cpu || !data?.memory || !data?.disk || !data?.network) {
      throw new Error('Invalid data shape');
    }
    return data;
  } catch (e) {
    // Fallback: generate mock data
    const now = Date.now();
    const N = 20;
    const make = (base: number, drift: number) => Array.from({ length: N }, (_, i) => ({ t: now - (N - i) * 1000, v: Math.max(0, base + Math.sin(i / 2) * drift + Math.random() * drift) }));
    // Mock extras: temperature, latency, IOPS
    const extras = [
      { name: 'Temperature', data: make(40, 6) },
      { name: 'Latency', data: make(20, 8) },
      { name: 'IOPS', data: make(120, 25) },
    ];
    return {
      cpu: make(40, 12),
      memory: make(60, 15),
      disk: make(55, 10),
      network: make(20, 8),
      extras,
    } as any;
  }
}

export default fetchMetrics;
