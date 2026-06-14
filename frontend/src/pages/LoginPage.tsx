import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

export function LoginPage() {
  const { isAuthenticated, isLoading, signInDev, isDevLoginAvailable } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate])

  const handleDevLogin = () => {
    signInDev()
    navigate('/')
  }

  return (
    <div className="container mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-md flex-col justify-center px-4 py-12">
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

        <Skeleton className="h-4 w-3/4 mx-auto" />
      </div>
    </div>
  )
}
