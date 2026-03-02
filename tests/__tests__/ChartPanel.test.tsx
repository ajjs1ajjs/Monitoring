import React from 'react'
import { render, screen } from '@testing-library/react'
import { ChartPanel } from '../../src/components/ChartPanel'

test('ChartPanel renders title', () => {
  const data = Array.from({ length: 5 }).map((_, i) => ({ x: i, y: i }))
  render(<ChartPanel title="Test" data={data} />)
  expect(screen.getByText('Test')).toBeInTheDocument()
})

test('ChartPanel renders legend when provided', () => {
  const data = Array.from({ length: 3 }).map((_, i) => ({ x: i, y: i * 2 }))
  render(<ChartPanel title="Test Legend" data={data} legend="Latency" />)
  // Legend text should appear
  const el = screen.getByText('Latency')
  expect(el).toBeInTheDocument()
})
