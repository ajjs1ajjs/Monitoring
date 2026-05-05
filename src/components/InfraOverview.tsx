import React from 'react'
import Card from './Card'
import ChartPanel from './ChartPanel'

type InfraOverviewProps = {
  cpu: { x: string | number; y: number }[]
  ram: { x: string | number; y: number }[]
}

/** Infrastructure Performance Overview
 *  - two charts: CPU and RAM usage
 */
const InfraOverview: React.FC<InfraOverviewProps> = ({ cpu, ram }) => {
  return (
    <Card title="Infrastructure Performance Overview" className="col-span-4">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <ChartPanel title="CPU" data={cpu} color="#4e9af6" height={180} legend="CPU" />
        <ChartPanel title="RAM" data={ram} color="#34d399" height={180} legend="RAM" />
      </div>
    </Card>
  )
}

export default InfraOverview
