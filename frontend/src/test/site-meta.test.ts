import { readFileSync } from 'node:fs'
import path from 'node:path'
import { SITE_DESCRIPTION, SITE_NAME, SITE_ORIGIN } from '@/lib/copy'

const indexHtml = readFileSync(path.resolve(__dirname, '../../index.html'), 'utf8')

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
})
