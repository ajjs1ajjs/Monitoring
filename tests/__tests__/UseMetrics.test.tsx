import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { useMetrics } from '../../src/hooks/useMetrics'
import { MetricsState } from '../../src/types/metrics'

// tiny test component to mount the hook
const TestHookComponent: React.FC<{ url?: string }>= ({ url }) => {
  const { cpu } = useMetrics(url, 100);
  return <div data-testid="cpu-length">{cpu.length}</div>
}

test('useMetrics fetches data (mock)', async () => {
  // mock fetch to return predictable data
  const mockData: MetricsState = { cpu: [{ t: 1, v: 10 }], memory: [], disk: [], network: [] }
  ;(global as any).fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => mockData })

  render(<TestHookComponent url="http://localhost:9182/metrics" />)
  await waitFor(() => expect((screen.getByTestId('cpu-length').textContent as string)).toBe('1'))
})
