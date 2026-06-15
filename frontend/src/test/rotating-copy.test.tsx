import { render, screen } from '@testing-library/react'
import { RotatingCopy } from '@/components/layout/RotatingCopy'

describe('RotatingCopy', () => {
  it('renders the first line immediately', () => {
    render(<RotatingCopy lines={['Hello', 'World', 'Third']} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders a single line without error', () => {
    render(<RotatingCopy lines={['Only line']} />)
    expect(screen.getByText('Only line')).toBeInTheDocument()
  })

  it('renders nothing for an empty lines array', () => {
    const { container } = render(<RotatingCopy lines={[]} />)
    expect(container.firstChild).toBeNull()
  })
})
