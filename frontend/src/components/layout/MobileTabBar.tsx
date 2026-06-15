import { Link, useLocation } from 'react-router-dom'
import { Bell, Home, List, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'

const tabs = [
  { to: '/', label: 'Home', icon: Home, match: (path: string) => path === '/' },
  { to: '/list', label: 'All', icon: List, match: (path: string) => path === '/list' },
  {
    to: '/notifications',
    label: 'Alerts',
    icon: Bell,
    match: (path: string) => path.startsWith('/notifications'),
  },
  {
    to: '/settings',
    label: 'Settings',
    icon: Settings,
    match: (path: string) => path.startsWith('/settings'),
  },
] as const

export function MobileTabBar() {
  const { pathname } = useLocation()

  return (
    <nav
      aria-label="Primary"
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur supports-[backdrop-filter]:bg-background/80 md:hidden"
    >
      <ul className="mx-auto flex max-w-5xl">
        {tabs.map(({ to, label, icon: Icon, match }) => {
          const active = match(pathname)
          return (
            <li key={to} className="flex-1">
              <Link
                to={to}
                className={cn(
                  'flex min-h-14 flex-col items-center justify-center gap-0.5 px-2 text-xs',
                  active ? 'font-medium text-foreground' : 'text-muted-foreground',
                )}
              >
                <Icon className="h-5 w-5" aria-hidden />
                {label}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
