import abercrombieLogo from '@/assets/retailers/abercrombie.svg'
import amazonCaLogo from '@/assets/retailers/amazon_ca.svg'
import appleCaLogo from '@/assets/retailers/apple_ca.svg'
import bestbuyCaLogo from '@/assets/retailers/bestbuy_ca.svg'
import indigoLogo from '@/assets/retailers/indigo.svg'
import nikeCaLogo from '@/assets/retailers/nike_ca.svg'
import palmisleskateLogo from '@/assets/retailers/palmisleskate.svg'
import tikiroomskateLogo from '@/assets/retailers/tikiroomskate.svg'

/** Known retailer slugs with bundled logo assets (excludes generic). */
export const RETAILER_LOGOS: Record<string, string> = {
  abercrombie: abercrombieLogo,
  amazon_ca: amazonCaLogo,
  apple_ca: appleCaLogo,
  bestbuy_ca: bestbuyCaLogo,
  indigo: indigoLogo,
  nike_ca: nikeCaLogo,
  palmisleskate: palmisleskateLogo,
  tikiroomskate: tikiroomskateLogo,
}

export function retailerLogoSrc(slug: string | null | undefined): string | undefined {
  if (!slug) return undefined
  return RETAILER_LOGOS[slug]
}
