import { useEffect, useState } from 'react'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function App() {
  const [apiMessage, setApiMessage] = useState<string>('Checking API…')

  useEffect(() => {
    let cancelled = false

    fetch(`${apiUrl}/`)
      .then((res) => res.json())
      .then((data: { message?: string }) => {
        if (!cancelled) {
          setApiMessage(data.message ?? 'API responded')
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiMessage('API unreachable — start the backend with make start')
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="app">
      <h1>Shopping Monitor</h1>
      <p className="tagline">Track prices and deals — scaffold ready for development.</p>
      <p className="status" data-testid="api-status">
        {apiMessage}
      </p>
    </main>
  )
}
