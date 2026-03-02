import React from 'react'
import DashboardLayout from '../components/DashboardLayout'
import ChartPanel from '../components/ChartPanel'
import Card from '../components/Card'
import { useMetrics } from '../hooks/useMetrics'

// Examples of dashboards with different metric mixes using the same style
const DashboardExamples: React.FC = () => {
  const { cpu, memory, disk, network } = useMetrics(undefined, 5000)
  const temp = useMetrics(undefined, 5000) // extras are part of data; main example uses extras inline
  // Since useMetrics is designed to fetch single url per call, we reuse the data sets via separate components if needed.
  // For simplicity, render three cards with different emphasis using the same data streams.
  return (
    <DashboardLayout title="Dashboard Examples" status="Online">
      <ChartPanel title="Overview CPU" data={cpu} color="#4e9af6" height={210} legend="CPU" />
      <ChartPanel title="Latency & Temperature" data={memory} color="#34d399" height={210} legend="Memory" />
      <ChartPanel title="IOPS & Network" data={disk} color="#f59e0b" height={210} legend="Disk" />
      <Card title="Combined Metrics" className="col-span-2">
        <div style={{ padding: 8 }}>
          <div>CPU: simulated</div>
          <div>Memory: simulated</div>
          <div>Disk: simulated</div>
          <div>Network: simulated</div>
        </div>
      </Card>
    </DashboardLayout>
  )
}

export default DashboardExamples
