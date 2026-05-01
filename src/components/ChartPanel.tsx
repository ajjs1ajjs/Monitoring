import React from 'react';

type Point = { x: string | number; y: number };
type ChartPanelProps = {
  title: string;
  data: Point[];
  color?: string;
  height?: number;
  legend?: string;
};

// Simple responsive SVG line chart with a filled area
export const ChartPanel: React.FC<ChartPanelProps> = ({ title, data, color = '#4e9af6', height = 220, legend }) => {
  if (!data || data.length < 2) {
    return (
      <div className="dashboard-card" style={{ height: height + 40 }}>
        <div className="card-title">{title}</div>
        <div className="chart-area" style={{ height: height }} />
      </div>
    );
  }

  const w = Math.max(320, data.length * 60);
  const h = height;
  const maxY = Math.max(...data.map((d) => d.y), 1);

  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - (d.y / maxY) * (h - 20) - 10;
    return `${x},${y}`;
  }).join(' ');

  const first = data[0];
  const lastX = (data.length - 1) / (data.length - 1) * w;
  const areaPath = `M 0 ${h} L ${pts} L ${w} ${h} Z`;
  const linePath = `M ${pts}`;

  // Build a correct line path by stepping through points
  const linePathSegments = data.map((d, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - (d.y / maxY) * (h - 20) - 10;
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');

  return (
    <section className="dashboard-card">
      <div className="card-title">{title}</div>
      {legend ? (
        <div style={{ fontSize: 11, color: '#93a3b8', marginTop: 4, display: 'flex', alignItems: 'center' }}>
          <span style={{ display: 'inline-block', width: 10, height: 10, background: color, borderRadius: 2, marginRight: 6 }} />
          <span>{legend}</span>
        </div>
      ) : null}
      <div className="chart-area" style={{ height: height }}>
        <svg width="100%" height={height} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
          {/* grid */}
          <g opacity={0.15}>
            {Array.from({ length: 4 }).map((_, idx) => (
              <line key={idx} x1={0} y1={((idx + 1) / 5) * h} x2={w} y2={((idx + 1) / 5) * h} stroke="#ffffff" strokeWidth={1} />
            ))}
          </g>
          {/* area */}
          <path d={areaPath} fill={color} fillOpacity={0.15} stroke="none" />
          {/* line */}
          <path d={linePathSegments} fill="none" stroke={color} strokeWidth={2} />
        </svg>
      </div>
    </section>
  );
};

export default ChartPanel;
