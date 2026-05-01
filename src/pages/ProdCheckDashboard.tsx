import React from 'react'
import DashboardLayout from '../components/DashboardLayout'
import ChartPanel from '../components/ChartPanel'
import { useMetrics } from '../hooks/useMetrics'

// Production check: predefinedProd URL (env override possible)
const ProdCheckDashboard: React.FC = () => {
  const prodUrl = (typeof window !== 'undefined' && (window as any).__EXPORTER_PROD_URL__) || ''
  const { cpu, memory, disk, network } = useMetrics(prodUrl || undefined, 5000)
  return (
    <DashboardLayout title="Prod Exporter Check" status={cpu.length ? 'Online' : 'Unknown'}>
      <ChartPanel title="CPU" data={cpu} color="#4e9af6" height={210} legend="CPU" />
      <ChartPanel title="Memory" data={memory} color="#34d399" height={210} legend="Memory" />
      <ChartPanel title="Disk" data={disk} color="#f59e0b" height={210} legend="Disk" />
      <ChartPanel title="Network" data={network} color="#a78bfa" height={210} legend="Network" />
    </DashboardLayout>
  )
}

export default ProdCheckDashboard
