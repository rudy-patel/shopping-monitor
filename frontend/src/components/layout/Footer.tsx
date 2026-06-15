import { footerQuips } from '@/lib/copy'
import { RotatingCopy } from '@/components/layout/RotatingCopy'

export function Footer() {
  return (
    <footer className="hidden border-t border-border md:block">
      <div className="container mx-auto flex max-w-5xl items-center justify-between px-4 py-3 text-xs text-muted-foreground">
        <span>© {new Date().getFullYear()} Someday</span>
        <span aria-hidden="true">
          <RotatingCopy lines={footerQuips} interval={8000} />
        </span>
      </div>
    </footer>
  )
}
