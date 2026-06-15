import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bell, Menu, Plus, User } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { AddProductDialog } from '@/components/add-product/AddProductDialog'
import {
  SearchTrigger,
  SearchTriggerMobile,
} from '@/components/search/SearchTrigger'
import { SearchCommandDialog } from '@/components/search/SearchCommandDialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useUnreadNotificationCount } from '@/hooks/useNotifications'

function formatUnreadBadge(count: number): string {
  if (count > 9) return '9+'
  return String(count)
}

export function TopNav() {
  const { signOut } = useAuth()
  const navigate = useNavigate()
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const { data: unreadCount = 0 } = useUnreadNotificationCount()

  const bellAriaLabel =
    unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'

  const handleSignOut = async () => {
    await signOut()
    navigate('/login')
  }

  const openSearch = useCallback(() => setSearchOpen(true), [])

  // Global ⌘K / Ctrl+K shortcut — Cursor-, Linear-, Raycast-style.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const isModifier = event.metaKey || event.ctrlKey
      if (!isModifier) return
      if (event.key.toLowerCase() !== 'k') return
      // Allow the shortcut inside inputs except when modifier+enter or pure typing.
      event.preventDefault()
      setSearchOpen((current) => !current)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const addProductButton = (
    <Button
      size="sm"
      className="h-11"
      aria-label="Add product"
      onClick={() => setAddDialogOpen(true)}
    >
      <Plus className="mr-2 h-4 w-4" />
      <span className="md:hidden">Add</span>
      <span className="hidden md:inline">Add Product</span>
    </Button>
  )

  const notificationsLink = (
    <Button variant="ghost" size="icon" className="h-11 w-11" asChild aria-label={bellAriaLabel}>
      <Link to="/notifications" className="relative">
        <Bell className="h-5 w-5" />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-foreground px-1 text-[10px] font-medium text-background">
            {formatUnreadBadge(unreadCount)}
          </span>
        ) : null}
      </Link>
    </Button>
  )

  const avatarMenu = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-11 w-11" aria-label="Account menu">
          <User className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onSelect={() => navigate('/history')}>Archived</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate('/settings')}>Settings</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleSignOut}>Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )

  const mobileMenu = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-11 w-11 md:hidden" aria-label="Menu">
          <Menu className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem onSelect={() => navigate('/history')}>Archived</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleSignOut}>Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 max-w-5xl items-center justify-between gap-3 px-4">
          <Link
            to="/"
            className="shrink-0 text-lg font-semibold tracking-tight"
          >
            Shopping Monitor
          </Link>

          <div className="mx-2 hidden flex-1 justify-center md:flex">
            <SearchTrigger onActivate={openSearch} />
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            <SearchTriggerMobile onActivate={openSearch} />
            {addProductButton}
            <div className="hidden items-center gap-2 md:flex">
              {notificationsLink}
              {avatarMenu}
            </div>
            {mobileMenu}
          </div>
        </div>
      </header>

      <AddProductDialog open={addDialogOpen} onOpenChange={setAddDialogOpen} />
      <SearchCommandDialog
        open={searchOpen}
        onOpenChange={setSearchOpen}
        onRequestUrlAdd={() => setAddDialogOpen(true)}
      />
    </>
  )
}
