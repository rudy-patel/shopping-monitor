import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('vercel.json', () => {
  it('rewrites client routes to index.html for SPA deep links', () => {
    const config = JSON.parse(
      readFileSync(resolve(process.cwd(), 'vercel.json'), 'utf8'),
    ) as { rewrites?: Array<{ source: string; destination: string }> }

    expect(config.rewrites).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: '/(.*)',
          destination: '/index.html',
        }),
      ]),
    )
  })
})
