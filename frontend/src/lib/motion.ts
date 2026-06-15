import { useReducedMotion } from 'framer-motion'

export const listItemTransition = {
  duration: 0.2,
  ease: [0.25, 0.1, 0.25, 1],
} as const

export function useMotionEnabled(): boolean {
  return !useReducedMotion()
}
