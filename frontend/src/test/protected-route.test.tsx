import { screen } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { renderWithProviders, clearAuthStorage } from './test-utils'

function ProtectedContent() {
  return <h1>Protected Content</h1>
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    clearAuthStorage()
  })

  it('redirects unauthenticated users to login and preserves intended path', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<h1>Login</h1>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/settings" element={<ProtectedContent />} />
        </Route>
      </Routes>,
      { route: '/settings', authenticated: false },
    )

    expect(await screen.findByRole('heading', { name: /login/i })).toBeInTheDocument()
  })

  it('renders child route when authenticated', async () => {
    renderWithProviders(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/settings" element={<ProtectedContent />} />
        </Route>
      </Routes>,
      { route: '/settings', authenticated: true },
    )

    expect(await screen.findByRole('heading', { name: /protected content/i })).toBeInTheDocument()
  })
})
