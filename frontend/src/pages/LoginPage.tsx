import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'

function getRedirectPath(state: unknown): string {
  const from = (state as { from?: string } | null)?.from
  return from && from !== '/login' ? from : '/'
}

export function LoginPage() {
  const { isAuthenticated, isLoading, signInDev, isDevLoginAvailable } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(getRedirectPath(location.state), { replace: true })
    }
  }, [isAuthenticated, isLoading, location.state, navigate])

  const handleDevLogin = () => {
    signInDev()
    navigate(getRedirectPath(location.state), { replace: true })
  }

  return (
    <div className="container mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-12">
      <div className="space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-semibold tracking-tight">Shopping Monitor</h1>
          <p className="text-muted-foreground">
            One organized home for things you want to buy.
          </p>
        </div>

        <div className="space-y-4 rounded-lg border border-border bg-background p-6">
          <Button className="w-full" disabled aria-disabled="true">
            Continue with Google
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Sign-in lands in T2.1
          </p>

          {isDevLoginAvailable && (
            <div className="space-y-2 border-t border-border pt-4">
              <Button variant="outline" className="w-full" onClick={handleDevLogin}>
                Dev login (local only)
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                For local development only. Not available in production builds.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
