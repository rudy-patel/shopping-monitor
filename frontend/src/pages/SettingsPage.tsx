import { useEffect, useState, type ReactNode } from 'react'
import { DeleteAccountDialog } from '@/components/settings/DeleteAccountDialog'
import { toast } from 'sonner'
import type { UseMutationResult } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { CURRENCIES, useCurrency } from '@/contexts/CurrencyContext'
import { useTheme } from '@/contexts/ThemeContext'
import { useProfile, useUpdateProfile } from '@/hooks/useProfile'
import type { Profile, ProfileUpdate } from '@/lib/profile'
import { cn } from '@/lib/utils'

type ProfileMutation = UseMutationResult<Profile, Error, ProfileUpdate>

type BooleanProfileField = keyof Pick<
  Profile,
  | 'notifications_enabled'
  | 'email_digest_enabled'
  | 'revisit_prompts_enabled'
  | 'revisit_on_sale_enabled'
  | 'revisit_stale_enabled'
>

function SettingsSection({
  title,
  children,
  intro,
}: {
  title: string
  intro?: string
  children: ReactNode
}) {
  return (
    <section className="space-y-4">
      <div className="border-b border-border pb-2">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        {intro ? <p className="mt-1 text-sm text-muted-foreground">{intro}</p> : null}
      </div>
      <div className="space-y-6">{children}</div>
    </section>
  )
}

function SettingRow({
  id,
  label,
  description,
  children,
  disabled,
}: {
  id: string
  label: string
  description?: string
  children: ReactNode
  disabled?: boolean
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between',
        disabled && 'opacity-60',
      )}
    >
      <div className="space-y-1">
        <Label htmlFor={id} className={disabled ? 'cursor-not-allowed' : undefined}>
          {label}
        </Label>
        {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

function ProfileSwitch({
  id,
  label,
  description,
  field,
  checked,
  updateProfile,
  disabled,
}: {
  id: string
  label: string
  description?: string
  field: BooleanProfileField
  checked: boolean
  updateProfile: ProfileMutation
  disabled?: boolean
}) {
  const [localChecked, setLocalChecked] = useState(checked)

  useEffect(() => {
    setLocalChecked(checked)
  }, [checked])

  const onCheckedChange = (next: boolean) => {
    if (disabled) return
    const previous = localChecked
    setLocalChecked(next)
    updateProfile.mutate(
      { [field]: next } as ProfileUpdate,
      {
        onError: () => {
          setLocalChecked(previous)
          toast.error("Couldn't save setting")
        },
      },
    )
  }

  return (
    <SettingRow id={id} label={label} description={description} disabled={disabled}>
      <Switch
        id={id}
        checked={localChecked}
        onCheckedChange={onCheckedChange}
        disabled={disabled || updateProfile.isPending}
        aria-label={label}
      />
    </SettingRow>
  )
}

function DefaultThresholdField({
  value,
  updateProfile,
}: {
  value: number
  updateProfile: ProfileMutation
}) {
  const [draft, setDraft] = useState(value.toString())

  useEffect(() => {
    setDraft(value.toString())
  }, [value])

  const commit = () => {
    const trimmed = draft.trim()
    if (!trimmed) {
      setDraft(value.toString())
      return
    }
    const parsed = Number(trimmed)
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > 95) {
      setDraft(value.toString())
      return
    }
    if (parsed === value) return
    updateProfile.mutate(
      { default_threshold_pct: parsed },
      {
        onError: () => {
          setDraft(value.toString())
          toast.error("Couldn't save threshold")
        },
      },
    )
  }

  return (
    <div className="grid max-w-xs gap-2">
      <Label htmlFor="default-threshold">Default threshold (%)</Label>
      <Input
        id="default-threshold"
        type="number"
        min={1}
        max={95}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        disabled={updateProfile.isPending}
      />
      <p className="text-xs text-muted-foreground">
        Used for new products unless you set a per-product threshold.
      </p>
    </div>
  )
}

function RevisitStaleDaysField({
  value,
  updateProfile,
  disabled,
}: {
  value: number
  updateProfile: ProfileMutation
  disabled: boolean
}) {
  const [draft, setDraft] = useState(value.toString())

  useEffect(() => {
    setDraft(value.toString())
  }, [value])

  const commit = () => {
    if (disabled) return
    const trimmed = draft.trim()
    if (!trimmed) {
      setDraft(value.toString())
      return
    }
    const parsed = Number(trimmed)
    if (!Number.isInteger(parsed) || parsed < 7 || parsed > 365) {
      setDraft(value.toString())
      return
    }
    if (parsed === value) return
    updateProfile.mutate(
      { revisit_stale_days: parsed },
      {
        onError: () => {
          setDraft(value.toString())
          toast.error("Couldn't save setting")
        },
      },
    )
  }

  return (
    <div className="grid max-w-xs gap-2">
      <Label htmlFor="revisit-stale-days">Days on list before a stale check-in</Label>
      <Input
        id="revisit-stale-days"
        type="number"
        min={7}
        max={365}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        disabled={disabled || updateProfile.isPending}
      />
    </div>
  )
}

function DisplayCurrencyField() {
  const { currency, setCurrency } = useCurrency()

  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-medium">Display currency</legend>
      <div className="flex flex-wrap gap-2">
        {CURRENCIES.map((code) => (
          <label
            key={code}
            className={cn(
              'flex cursor-pointer items-center gap-2 rounded-md border border-border px-3 py-2 text-sm transition-colors',
              currency === code && 'border-primary bg-primary/5',
            )}
          >
            <input
              type="radio"
              name="display-currency"
              value={code}
              checked={currency === code}
              onChange={() => setCurrency(code)}
              className="sr-only"
            />
            {code}
          </label>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Prices are stored in CAD; conversion is for display only.
      </p>
    </fieldset>
  )
}

function ThemeField() {
  const { theme, setTheme } = useTheme()

  return (
    <SettingRow
      id="dark-mode"
      label="Dark mode"
      description="Use a dark color scheme across the app."
    >
      <Switch
        id="dark-mode"
        checked={theme === 'dark'}
        onCheckedChange={(checked) => setTheme(checked ? 'dark' : 'light')}
        aria-label="Dark mode"
      />
    </SettingRow>
  )
}

function SettingsSkeleton() {
  return (
    <div className="space-y-8">
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  )
}

export function SettingsPage() {
  const { data: profile, isLoading, isError } = useProfile()
  const updateProfile = useUpdateProfile()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  if (isLoading || !profile) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <h1 className="mb-8 text-2xl font-semibold tracking-tight">Settings</h1>
        {isError ? (
          <p className="text-sm text-destructive">Could not load settings. Try refreshing the page.</p>
        ) : (
          <SettingsSkeleton />
        )}
      </div>
    )
  }

  const revisitMasterOff = !profile.revisit_prompts_enabled
  const revisitStaleOff = revisitMasterOff || !profile.revisit_stale_enabled

  return (
    <div className="container mx-auto max-w-5xl space-y-10 px-4 py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>

      <SettingsSection title="Display">
        <DisplayCurrencyField />
        <ThemeField />
      </SettingsSection>

      <SettingsSection title="Notifications">
        <ProfileSwitch
          id="notifications-enabled"
          label="In-app notifications"
          description="Price drops, scrape issues, and other alerts in your notification list."
          field="notifications_enabled"
          checked={profile.notifications_enabled}
          updateProfile={updateProfile}
        />
        <DefaultThresholdField
          value={profile.default_threshold_pct}
          updateProfile={updateProfile}
        />
        <ProfileSwitch
          id="email-digest-enabled"
          label="Daily email digest"
          description="A summary of unread notifications. Your in-app list remains the source of truth."
          field="email_digest_enabled"
          checked={profile.email_digest_enabled}
          updateProfile={updateProfile}
        />
      </SettingsSection>

      <SettingsSection
        title="Revisit prompts"
        intro="Occasional check-ins on items that have been on your list a while."
      >
        <ProfileSwitch
          id="revisit-prompts-enabled"
          label="Revisit prompts"
          description="Enable gentle nudges about older list items."
          field="revisit_prompts_enabled"
          checked={profile.revisit_prompts_enabled}
          updateProfile={updateProfile}
        />
        <ProfileSwitch
          id="revisit-on-sale-enabled"
          label="On-sale nudges"
          description="Suggest a second look when something old is meaningfully on sale."
          field="revisit_on_sale_enabled"
          checked={profile.revisit_on_sale_enabled}
          updateProfile={updateProfile}
          disabled={revisitMasterOff}
        />
        <ProfileSwitch
          id="revisit-stale-enabled"
          label="Stale-list nudges"
          description="Gently ask whether you still want items that have gone quiet."
          field="revisit_stale_enabled"
          checked={profile.revisit_stale_enabled}
          updateProfile={updateProfile}
          disabled={revisitMasterOff}
        />
        <RevisitStaleDaysField
          value={profile.revisit_stale_days}
          updateProfile={updateProfile}
          disabled={revisitStaleOff}
        />
      </SettingsSection>

      <SettingsSection title="Account">
        <p className="text-sm text-muted-foreground">
          Permanently deleting your account removes your products, price history, and
          notifications.
        </p>
        <div className="space-y-2">
          <Button
            type="button"
            variant="destructive"
            onClick={() => setDeleteDialogOpen(true)}
          >
            Delete account
          </Button>
        </div>
        <DeleteAccountDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} />
      </SettingsSection>
    </div>
  )
}
