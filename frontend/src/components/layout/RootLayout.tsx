import { Outlet } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'

export function RootLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNav />
      <main>
        <Outlet />
      </main>
    </div>
  )
}
