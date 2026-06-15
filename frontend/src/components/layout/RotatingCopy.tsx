import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface RotatingCopyProps {
  lines: string[]
  interval?: number
  className?: string
}

export function RotatingCopy({ lines, interval = 4000, className }: RotatingCopyProps) {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (lines.length <= 1) return
    const id = setInterval(() => {
      setIndex((current) => (current + 1) % lines.length)
    }, interval)
    return () => clearInterval(id)
  }, [lines.length, interval])

  return (
    <span className={cn('relative inline-block', className)} aria-live="polite" aria-atomic="true">
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={index}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.4, ease: 'easeInOut' }}
          className="block"
        >
          {lines[index]}
        </motion.span>
      </AnimatePresence>
    </span>
  )
}
