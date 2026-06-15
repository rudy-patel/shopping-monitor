import { Outlet, useLocation } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'
import { MobileTabBar } from '@/components/layout/MobileTabBar'

export function RootLayout() {
  const { pathname } = useLocation()
  const showNav = pathname !== '/login'

  return (
    <div className="min-h-screen bg-background text-foreground">
      {showNav && <TopNav />}
      <main id="main-content" className={showNav ? 'pb-20 md:pb-0' : undefined}>
        <Outlet />
      </main>
      {showNav ? <MobileTabBar /> : null}
    </div>
  )
}
