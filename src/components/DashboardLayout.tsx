import React, { useEffect } from 'react'

export const DashboardLayout: React.FC<LayoutProps> = ({ title = 'Dashboard', children, status, theme = 'dark' }) => {
  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as any).showSection = (section: string) => {
        try {
          const elements = document.querySelectorAll(`[data-section='${section}']`)
          if (elements.length > 0) {
            elements.forEach((el) => {
              const he = el as HTMLElement
              he.style.display = he.style.display === 'none' ? '' : 'none'
            })
            return
          }
          const byId = document.getElementById(section)
          if (byId) {
            byId.style.display = byId.style.display === 'none' ? '' : 'none'
          }
        } catch (e) {
          // eslint-disable-next-line no-console
          console.error('showSection failed', e)
        }
      }
    }
  }, [])

  const statusColor = status === 'Online' ? '#22c55e' : status === 'Offline' ? '#f87171' : '#9CA3AF';
// Define a safe global showSection handler in a React lifecycle way
useEffect(() => {
  if (typeof window !== 'undefined' && typeof (window as any).showSection !== 'function') {
    ;(window as any).showSection = (section: string) => {
      try {
        const elements = document.querySelectorAll(`[data-section='${section}']`)
        if (elements.length > 0) {
          elements.forEach((el) => {
            const he = el as HTMLElement
            he.style.display = he.style.display === 'none' ? '' : 'none'
          })
          return
        }
        const byId = document.getElementById(section)
        if (byId) {
          byId.style.display = byId.style.display === 'none' ? '' : 'none'
        }
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('showSection failed', e)
      }
    }
  }
}, [])
import '../styles/dashboard.css';
// Note: No inline script injection; showSection is provided via React effect above

type LayoutProps = {
  title?: string;
  children: React.ReactNode;
  status?: string; // e.g. 'Online' or 'Offline'
  theme?: 'dark' | 'light';
};

export const DashboardLayout: React.FC<LayoutProps> = ({ title = 'Dashboard', children, status, theme = 'dark' }) => {
  const statusColor = status === 'Online' ? '#22c55e' : status === 'Offline' ? '#f87171' : '#9CA3AF';
  return (
    <>
      <div className="dashboard-layout" data-theme={theme} style={{ fontFamily: 'Inter, system-ui, Arial' }}>
      <header className="dashboard-header">
        <span style={{ marginRight: 12 }}>{/* logo placeholder */}📊</span>
        <span style={{ fontWeight: 700 }}>{title}</span>
        {typeof status === 'string' && (
          <span style={{ display: 'inline-flex', alignItems: 'center', marginLeft: 12 }}>
            <span
              aria-label="exporter-status-dot"
              style={{ width: 8, height: 8, borderRadius: 99, background: statusColor, display: 'inline-block', marginRight: 6 }}
            />
            <span
              aria-label="exporter-status"
              style={{ padding: '2px 8px', borderRadius: 6, fontSize: 12, fontWeight: 600, background: '#1e293b' }}
            >
              {status}
            </span>
          </span>
        )}
      </header>
      <main className="dashboard-grid" style={{ paddingTop: 0 }}>{children}</main>
    </div>
    </>
  );
};

export default DashboardLayout;
