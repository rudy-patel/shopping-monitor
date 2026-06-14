import { Skeleton } from '@/components/ui/skeleton'

export function SettingsPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Settings</h1>
      <p className="mb-8 text-muted-foreground">
        Manage your profile, theme, currency, and notification preferences.
      </p>
      <div className="space-y-6">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
      <p className="mt-8 text-sm text-muted-foreground">Coming in T4.2</p>
    </div>
  )
}
