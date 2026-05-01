// Design tokens for a unified dark dashboard style (ASCII comments)
export const tokens = {
  colors: {
    background: '#0b0f14', // page background
    surface: '#141a22', // panels/cards background
    text: '#e6e6e6',
    muted: '#8a97a6',
    border: '#2a3640',
    primary: '#4e9af6',
    accent: '#f5a623',
    success: '#3bd07f',
    danger: '#f05050',
    chartStroke: '#4e9af6',
  },
  typography: {
    fontFamily: `'Inter', 'Segoe UI', Roboto, Arial, sans-serif`,
    baseSize: '14px',
    smallSize: '12px',
    titleWeight: 600,
  },
  radii: {
    card: '12px',
  },
  shadows: {
    card: '0 2px 8px rgba(0,0,0,0.4)',
  },
};

export type Tokens = typeof tokens;
