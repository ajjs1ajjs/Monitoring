import React from 'react';
import DashboardLayout from '../components/DashboardLayout';
import ChartPanel from '../components/ChartPanel';
import Card from '../components/Card';
import { useMetrics } from '../hooks/useMetrics';
import { useExporterUrl } from '../hooks/useExporterUrl';
import { EXPORTER_METRICS_ENDPOINT, EXPORTER_INTERVAL_MS } from '../config/exporterConfig';
import useExporterHealth from '../hooks/useExporterHealth';

// Demo page showing a unified dashboard that consumes exporter metrics
// Uses live metrics via useMetrics hook

// Locker hook usage and data transformation
const DashboardDemo: React.FC = () => {
  const [exporterUrl, setExporterUrl] = useExporterUrl();
  const [theme, setTheme] = React.useState<'dark'|'light'>('dark');
  const urlForMetrics = exporterUrl?.trim() ? exporterUrl.trim() : undefined;
  const { cpu, memory, disk, network, extras } = useMetrics(urlForMetrics, EXPORTER_INTERVAL_MS);
  const health = useExporterHealth(urlForMetrics, 5000);

  // data from useMetrics is already in chart-friendly format: { x, y }[]

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
  return (
    <DashboardLayout title="Dashboard" status={health} theme={theme}>
      <div style={{ gridColumn: 'span 4', padding: 8 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#a0aec0', marginBottom: 6 }}>Exporter URL</label>
        <input
          value={exporterUrl}
          onChange={(e) => setExporterUrl(e.target.value)}
          placeholder={EXPORTER_METRICS_ENDPOINT}
          style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid #2a3640', background: '#0b0f14', color: '#e6e6e6' }}
        />
        <div style={{ marginTop: 6, display: 'flex', gap: 8 }}>
          <button
            onClick={() => setExporterUrl('http://localhost:9182/metrics')}
            style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #2a3640', background: '#1f2a3a', color: '#e2e8f0', cursor: 'pointer' }}
          >
            Fill from exporter (9182/metrics)
          </button>
          <button
            onClick={() => setExporterUrl('http://127.0.0.1:8090/metrics')}
            style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #2a3640', background: '#1f2a3a', color: '#e2e8f0', cursor: 'pointer' }}
          >
            Also test 8090/metrics
          </button>
        </div>
        <div style={{ fontSize: 11, color: '#7c8a9b', marginTop: 6 }}>
          Use this to point to your exporter. If left empty, default endpoint is used.
        </div>
        <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
          <button onClick={toggleTheme} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #2a3640', background: '#1f2a3a', color: '#e2e8f0' }}>
            Toggle Theme
          </button>
        </div>
      </div>
      {[
        { key: 'cpu', title: 'CPU Usage', data: cpu, color: '#4e9af6' },
        { key: 'memory', title: 'Memory Usage', data: memory, color: '#34d399' },
        { key: 'disk', title: 'Disk Usage', data: disk, color: '#f59e0b' },
        { key: 'network', title: 'Network Traffic', data: network, color: '#a78bfa' },
      ].map((m) => (
        <ChartPanel key={m.key} title={m.title} data={m.data} color={m.color} height={210} legend={m.title} />
      ))}
      {extras?.length
        ? extras.map((ex, idx) => (
            <ChartPanel
              key={ex.name ?? `extra-${idx}`}
              title={ex.name}
              data={ex.data}
              color={['#22c55e', '#f472b6', '#3b82f6', '#f97316'][idx % 4]}
              height={210}
              legend={ex.name}
            />
          ))
        : null}
      <Card title="Server Overview" className="col-span-2">
        <div style={{ padding: 8 }}>
          <p style={{ margin: 0, color: '#cbd5e1' }}>Test PC</p>
          <p style={{ margin: '6px 0 0', fontSize: 12, color: '#8b9bb4' }}>CPU 3.9%, MEM 41.9%, DISK 59.6%</p>
        </div>
      </Card>
    </DashboardLayout>
  );
};

export default DashboardDemo;
