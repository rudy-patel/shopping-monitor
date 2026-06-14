import { Outlet, useLocation } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'

export function RootLayout() {
  const { pathname } = useLocation()
  const showNav = pathname !== '/login'

  return (
    <div className="min-h-screen bg-background text-foreground">
      {showNav && <TopNav />}
      <main>
        <Outlet />
      </main>
    </div>
  )
}
