import { describe, expect, it } from 'vitest'

import en from './locales/en.json'
import hi from './locales/hi.json'

type Tree = { [key: string]: string | Tree }

function keys(tree: Tree, prefix = ''): string[] {
  return Object.entries(tree).flatMap(([k, v]) =>
    typeof v === 'string' ? [`${prefix}${k}`] : keys(v, `${prefix}${k}.`),
  )
}

function values(tree: Tree): string[] {
  return Object.values(tree).flatMap((v) => (typeof v === 'string' ? [v] : values(v)))
}

describe('translation catalogues', () => {
  it('Hindi and English define exactly the same keys', () => {
    expect(keys(hi).sort()).toEqual(keys(en).sort())
  })

  it('no translation is empty', () => {
    for (const value of [...values(hi), ...values(en)]) {
      expect(value.trim()).not.toBe('')
    }
  })
})
