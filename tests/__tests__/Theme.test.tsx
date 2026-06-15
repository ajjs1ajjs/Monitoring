import React from 'react'
import { render } from '@testing-library/react'
import DashboardLayout from '../../src/components/DashboardLayout'

test('DashboardLayout dark theme applies data-theme attribute', () => {
  const { container } = render(
    <DashboardLayout title="Test" theme="dark">
      <div>Content</div>
    </DashboardLayout>
  )
  const root = container.firstElementChild as HTMLElement
  expect(root).toBeTruthy()
  expect(root.getAttribute('data-theme')).toBe('dark')
})

test('DashboardLayout light theme applies data-theme attribute', () => {
  const { container } = render(
    <DashboardLayout title="Test" theme="light">
      <div>Content</div>
    </DashboardLayout>
  )
  const root = container.firstElementChild as HTMLElement
  expect(root).toBeTruthy()
  expect(root.getAttribute('data-theme')).toBe('light')
})
