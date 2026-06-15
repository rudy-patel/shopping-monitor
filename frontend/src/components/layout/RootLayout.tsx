import { Outlet, useLocation } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'
import { MobileTabBar } from '@/components/layout/MobileTabBar'
import { Footer } from '@/components/layout/Footer'

export function RootLayout() {
  const { pathname } = useLocation()
  const showNav = pathname !== '/login'

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {showNav && <TopNav />}
      <main id="main-content" className={showNav ? 'flex-1 pb-20 md:pb-0' : undefined}>
        <Outlet />
      </main>
      {showNav ? <MobileTabBar /> : null}
      {showNav ? <Footer /> : null}
    </div>
  )
}
