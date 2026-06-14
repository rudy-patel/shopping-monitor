import { useCallback } from 'react'
import { useCurrency } from '@/contexts/CurrencyContext'
import { formatCadCents } from '@/lib/format'
import { useFxRates } from '@/hooks/useFxRates'

export function useFormatPriceCents() {
  const { currency } = useCurrency()
  const { data: fx, isError } = useFxRates()

  return useCallback(
    (cents: number | null | undefined) => {
      if (cents == null) return '—'

      const quote = isError || !fx?.rates ? 'CAD' : currency
      if (quote === 'CAD') {
        return formatCadCents(cents)
      }

      const rate = Number(fx.rates[quote])
      if (!Number.isFinite(rate) || rate <= 0) {
        return formatCadCents(cents)
      }

      const major = (cents / 100) * rate
      return new Intl.NumberFormat('en-CA', {
        style: 'currency',
        currency: quote,
      }).format(major)
    },
    [currency, fx, isError],
  )
}
