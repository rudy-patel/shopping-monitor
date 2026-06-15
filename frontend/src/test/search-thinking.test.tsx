import { render, screen } from '@testing-library/react'
import { SearchThinking } from '@/components/search/SearchThinking'

vi.mock('@/lib/motion', () => ({
  useMotionEnabled: () => false,
}))

describe('SearchThinking', () => {
  it('shows the query and a loading status message', () => {
    render(<SearchThinking query="airpods" />)

    expect(screen.getByTestId('search-loading')).toBeInTheDocument()
    expect(screen.getByText(/searching for/i)).toBeInTheDocument()
    expect(screen.getByText('airpods')).toBeInTheDocument()
    expect(screen.getByText(/scouring canadian retailers/i)).toBeInTheDocument()
  })
})
