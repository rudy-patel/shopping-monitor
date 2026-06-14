import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext'
import { clearAuthStorage } from './test-utils'

function ThemeToggleButton() {
  const { theme, toggleTheme } = useTheme()
  return (
    <button type="button" onClick={toggleTheme}>
      Current theme: {theme}
    </button>
  )
}

describe('ThemeContext', () => {
  beforeEach(() => {
    clearAuthStorage()
    document.documentElement.classList.remove('dark')
  })

  it('defaults to light theme', () => {
    render(
      <ThemeProvider>
        <ThemeToggleButton />
      </ThemeProvider>,
    )

    expect(screen.getByRole('button', { name: /current theme: light/i })).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('toggles theme and persists to localStorage', async () => {
    const user = userEvent.setup()

    render(
      <ThemeProvider>
        <ThemeToggleButton />
      </ThemeProvider>,
    )

    await user.click(screen.getByRole('button', { name: /current theme: light/i }))

    expect(screen.getByRole('button', { name: /current theme: dark/i })).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')

    await user.click(screen.getByRole('button', { name: /current theme: dark/i }))

    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('theme')).toBe('light')
  })
})
