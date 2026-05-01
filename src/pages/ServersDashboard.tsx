import React from 'react'
import DashboardLayout from '../components/DashboardLayout'
import Card from '../components/Card'

const ServersDashboard: React.FC = () => {
  const servers = [
    { name: 'Test PC', cpu: '3.9%', mem: '41.9%', disk: '59.6%', net: '0.0/0.0 MB' }
  ]
  return (
    <DashboardLayout title="Servers" status="Online">
      {servers.map((s) => (
        <Card key={s.name} title={s.name} className="col-span-2">
          <div style={{ padding: 8 }}>
            <div>CPU: {s.cpu}</div>
            <div>Memory: {s.mem}</div>
            <div>Disk: {s.disk}</div>
            <div>Network: {s.net}</div>
          </div>
        </Card>
      ))}
      {/* Unified style metric panel for a quick CPU chart */}
      <Card title="Test PC - CPU" className="col-span-2">
        <div style={{ padding: 8 }}>
          <div>CPU Load</div>
          <div style={{ height: 120, background: '#0b0f14', borderRadius: 6, marginTop: 8 }} />
        </div>
      </Card>
    </DashboardLayout>
  )
}

export default ServersDashboard
