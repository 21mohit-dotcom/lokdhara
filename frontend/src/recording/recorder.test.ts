import { describe, expect, it } from 'vitest'

import { extensionFor, pickMimeType } from './recorder'

describe('recording format', () => {
  it('prefers Opus in WebM and falls back to what the browser has', () => {
    expect(pickMimeType(() => true)).toBe('audio/webm;codecs=opus')
    // Safari records only MP4/AAC.
    expect(pickMimeType((type) => type === 'audio/mp4')).toBe('audio/mp4')
    expect(pickMimeType(() => false)).toBeUndefined()
  })

  it('names the file after the format actually recorded', () => {
    expect(extensionFor('audio/webm;codecs=opus')).toBe('webm')
    expect(extensionFor('audio/mp4;codecs=mp4a.40.2')).toBe('m4a')
    expect(extensionFor('audio/ogg;codecs=opus')).toBe('ogg')
  })
})
