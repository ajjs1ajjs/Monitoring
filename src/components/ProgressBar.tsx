import React from 'react'

type ProgressBarProps = {
  value: number // 0 - 100
  height?: number
}

// Thick gradient progress bar
const ProgressBar: React.FC<ProgressBarProps> = ({ value, height = 14 }) => {
  const clamped = Math.max(0, Math.min(100, value))
  const gradient = `linear-gradient(90deg, #34d399, #f59e0b, #f87171)`
  return (
    <div style={{ width: '100%', height, background: '#1f2a3a', borderRadius: height / 2, overflow: 'hidden', border: '1px solid #2a3640' }}>
      <div
        style={{ width: `${clamped}%`, height: '100%', background: gradient, borderRadius: height / 2, transition: 'width 0.3s ease' }}
      />
    </div>
  )
}

export default ProgressBar
