import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bell, Menu, Plus, User } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { AddProductDialog } from '@/components/add-product/AddProductDialog'
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
  const { data: unreadCount = 0 } = useUnreadNotificationCount()

  const bellAriaLabel =
    unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'

  const handleSignOut = async () => {
    await signOut()
    navigate('/login')
  }

  const addProductButton = (
    <Button size="sm" onClick={() => setAddDialogOpen(true)}>
      <Plus className="mr-2 h-4 w-4" />
      Add Product
    </Button>
  )

  const notificationsLink = (
    <Button variant="ghost" size="icon" asChild aria-label={bellAriaLabel}>
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
        <Button variant="ghost" size="icon" aria-label="Account menu">
          <User className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onSelect={() => navigate('/history')}>Archived products</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate('/settings')}>Settings</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleSignOut}>Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )

  const mobileMenu = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Menu">
          <Menu className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem onSelect={() => setAddDialogOpen(true)}>Add Product</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate('/notifications')}>Notifications</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate('/history')}>Archived products</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate('/settings')}>Settings</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={handleSignOut}>Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Shopping Monitor
          </Link>

          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-2 md:flex">
              {addProductButton}
              {notificationsLink}
              {avatarMenu}
            </div>
            {mobileMenu}
          </div>
        </div>
      </header>

      <AddProductDialog open={addDialogOpen} onOpenChange={setAddDialogOpen} />
    </>
  )
}
