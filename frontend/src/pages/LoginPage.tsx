import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '@/contexts/AuthContext'
import { BrandMark } from '@/components/brand/BrandMark'
import { RotatingCopy } from '@/components/layout/RotatingCopy'
import { LoginSplashStickers } from '@/components/login/LoginSplashStickers'
import { Button } from '@/components/ui/button'
import { loginTaglines } from '@/lib/copy'
import { loginSplashBackgroundClass } from '@/lib/login-splash'
import { cn } from '@/lib/utils'

function getRedirectPath(state: unknown): string {
  const from = (state as { from?: string } | null)?.from
  return from && from !== '/login' ? from : '/'
}

export function LoginPage() {
  const { isAuthenticated, isLoading, signInWithGoogle, signInDev, isDevLoginAvailable } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(getRedirectPath(location.state), { replace: true })
    }
  }, [isAuthenticated, isLoading, location.state, navigate])

  const handleGoogleSignIn = async () => {
    try {
      await signInWithGoogle()
    } catch {
      toast.error('Could not start Google sign-in. Please try again.')
    }
  }

  const handleDevLogin = () => {
    signInDev()
    navigate(getRedirectPath(location.state), { replace: true })
  }

  return (
    <div
      className={cn(
        'relative isolate flex min-h-screen w-full flex-col overflow-hidden',
        loginSplashBackgroundClass,
      )}
    >
      <LoginSplashStickers />

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 py-16">
        <div className="flex w-full max-w-md flex-col items-center text-center">
          <BrandMark size="hero" />

          <p className="mt-8 max-w-sm text-balance text-sm text-muted-foreground sm:text-base">
            <RotatingCopy lines={loginTaglines} interval={4000} />
          </p>

          <div className="mt-10 w-full max-w-xs space-y-3">
            <Button
              size="lg"
              className="w-full shadow-sm"
              onClick={() => void handleGoogleSignIn()}
            >
              Continue with Google
            </Button>

            {isDevLoginAvailable && (
              <div className="space-y-2 pt-2">
                <Button
                  variant="outline"
                  className="w-full bg-background/80 backdrop-blur-sm"
                  onClick={handleDevLogin}
                >
                  Dev login (local only)
                </Button>
                <p className="text-center text-[11px] text-muted-foreground">
                  For local development only. Not available in production builds.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
