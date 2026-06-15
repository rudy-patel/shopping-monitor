import { useEffect, useState } from 'react'

const STORAGE_KEY = 'shopping-monitor:just-added-product'

/** Minimum time the category "thinking" UI stays visible after first mount. */
export const MIN_CATEGORY_THINKING_MS = 2500

/** How long the post-sort hint pill stays visible after thinking completes. */
export const CATEGORY_REVEAL_HINT_MS = 3000

const IDLE_STATE: JustAddedCategoryThinking = {
  isThinking: false,
  showRevealHint: false,
  categorySource: null,
}

interface JustAddedProductSession {
  productId: string
  categorySource: string
  /** Set on first thinking UI mount so detail + dashboard share one deadline. */
  thinkingUntil: number | null
}

function readSession(): JustAddedProductSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as JustAddedProductSession
  } catch {
    return null
  }
}

function writeSession(session: JustAddedProductSession): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
}

export function markProductJustAdded(productId: string, categorySource: string): void {
  writeSession({
    productId,
    categorySource,
    thinkingUntil: null,
  })
}

export function clearJustAddedProduct(): void {
  sessionStorage.removeItem(STORAGE_KEY)
}

function ensureThinkingUntil(session: JustAddedProductSession): number {
  if (session.thinkingUntil === null) {
    session.thinkingUntil = Date.now() + MIN_CATEGORY_THINKING_MS
    writeSession(session)
  }
  return session.thinkingUntil
}

export function revealHintLabel(categorySource: string): string {
  return categorySource === 'manual' ? 'Saved as picked' : 'Sorted by AI'
}

export interface JustAddedCategoryThinking {
  isThinking: boolean
  showRevealHint: boolean
  categorySource: string | null
}

function thinkingStateForSession(
  productId: string,
  session: JustAddedProductSession,
): JustAddedCategoryThinking {
  if (session.thinkingUntil === null) {
    return {
      isThinking: true,
      showRevealHint: false,
      categorySource: session.categorySource,
    }
  }

  const now = Date.now()
  const isThinking = now < session.thinkingUntil
  const showRevealHint =
    !isThinking && now < session.thinkingUntil + CATEGORY_REVEAL_HINT_MS

  return {
    isThinking,
    showRevealHint,
    categorySource: session.categorySource,
  }
}

function peekThinkingState(productId: string): JustAddedCategoryThinking {
  const session = readSession()
  if (!session || session.productId !== productId) {
    return IDLE_STATE
  }
  return thinkingStateForSession(productId, session)
}

export function useJustAddedCategoryThinking(productId: string): JustAddedCategoryThinking {
  const [state, setState] = useState(() => peekThinkingState(productId))

  useEffect(() => {
    const session = readSession()
    if (!session || session.productId !== productId) {
      setState(IDLE_STATE)
      return
    }

    const thinkingUntil = ensureThinkingUntil(session)

    const refresh = () =>
      setState(
        thinkingStateForSession(productId, {
          ...session,
          thinkingUntil,
        }),
      )

    refresh()

    const timers: number[] = []
    const schedule = (delayMs: number, fn: () => void) => {
      timers.push(window.setTimeout(fn, Math.max(0, delayMs)))
    }

    schedule(thinkingUntil - Date.now(), refresh)
    schedule(thinkingUntil + CATEGORY_REVEAL_HINT_MS - Date.now(), () => {
      clearJustAddedProduct()
      setState(IDLE_STATE)
    })

    return () => {
      for (const timer of timers) {
        window.clearTimeout(timer)
      }
    }
  }, [productId])

  return state
}
