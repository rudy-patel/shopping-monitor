import { readFileSync } from 'node:fs'
import path from 'node:path'
import { loginTaglines, SITE_DESCRIPTION, SITE_NAME, SITE_ORIGIN } from '@/lib/copy'

const indexHtml = readFileSync(path.resolve(__dirname, '../../index.html'), 'utf8')
const webManifest = readFileSync(
  path.resolve(__dirname, '../../public/site.webmanifest'),
  'utf8',
)
const ogImageSvg = readFileSync(
  path.resolve(__dirname, '../../public/og-image.svg'),
  'utf8',
)

const EM_DASH = '\u2014'

describe('index.html share meta', () => {
  it('includes favicon, touch icon, and web manifest links', () => {
    expect(indexHtml).toContain('href="/favicon.svg"')
    expect(indexHtml).toContain('href="/apple-touch-icon.png"')
    expect(indexHtml).toContain('href="/site.webmanifest"')
  })

  it('keeps description and OG copy aligned with copy.ts constants', () => {
    expect(indexHtml).toContain(`<title>${SITE_NAME}</title>`)
    expect(indexHtml).toContain(SITE_DESCRIPTION)
    expect(indexHtml).toContain(`property="og:site_name" content="${SITE_NAME}"`)
    expect(indexHtml).toContain(`${SITE_ORIGIN}/og-image.png`)
  })

  it('declares Open Graph image dimensions for link previews', () => {
    expect(indexHtml).toContain('property="og:image:width" content="1200"')
    expect(indexHtml).toContain('property="og:image:height" content="630"')
    expect(indexHtml).toContain('name="twitter:card" content="summary_large_image"')
  })

  it('avoids em dashes in share-preview copy', () => {
    expect(indexHtml).not.toContain(EM_DASH)
  })

  it('keeps web manifest description aligned with copy.ts', () => {
    expect(webManifest).toContain(SITE_DESCRIPTION)
    expect(webManifest).not.toContain(EM_DASH)
  })

  it('keeps og-image.svg tagline aligned with login splash copy', () => {
    expect(ogImageSvg).toContain(loginTaglines[0])
    expect(ogImageSvg).not.toContain(EM_DASH)
  })
})
