import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import i18n from '../i18n'
import { fakeServer, SESSION } from '../test/fakeServer'
import { renderApp } from '../test/render'

const REVISION = {
  id: 'rev1',
  revision_number: 2,
  content: 'यह एक परीक्षण वाक्य है।',
  origin: 'human_contributor',
  based_on_revision_id: 'rev0',
  source_revision_id: null,
  detected_scripts: ['Deva'],
  uncertainty_markup: false,
  verification_status: 'unverified',
  change_note: null,
  created_at: '2026-10-15T10:00:00Z',
}

const LAYER = {
  id: 'l1',
  layer_type: 'transcription',
  recording_id: 'rec1',
  source_layer_id: null,
  entry_type: null,
  language_tag: 'unr',
  script_code: 'Deva',
  current_revision: REVISION,
  source_changed: false,
  script_mismatch: false,
}

const TRANSLATION = {
  ...LAYER,
  id: 'l2',
  layer_type: 'translation',
  recording_id: null,
  source_layer_id: 'l1',
  language_tag: 'en',
  script_code: 'Latn',
  current_revision: { ...REVISION, id: 'rev2', revision_number: 1, content: 'A test sentence.' },
  source_changed: true,
}

export const DETAIL = {
  id: 'sub1',
  client_submission_id: 'c1',
  kind: 'audio_text',
  content_type: 'story',
  title: 'River story',
  status: 'accepted',
  recording_mode: 'free',
  created_at: '2026-10-14T10:00:00Z',
  submitted_at: '2026-10-14T10:05:00Z',
  recordings: [
    {
      id: 'rec1',
      upload_status: 'promoted',
      size_bytes: 1000,
      duration_ms: 3000,
      quality_flags: [],
      created_at: '2026-10-14T10:01:00Z',
    },
  ],
  // The translation comes first here; the page shows it after its source.
  text_layers: [TRANSLATION, LAYER],
}

beforeEach(async () => {
  await i18n.changeLanguage('en')
})

describe('one submission', () => {
  it('shows the status, the recording, and each text after the one it translates', async () => {
    fakeServer({
      'GET /auth/me': () => ({ body: SESSION }),
      'GET /submissions/sub1': () => ({ body: DETAIL }),
      'GET /recordings/rec1/playback': () => ({
        body: { sources: [{ url: '/files/rec1.webm', content_type: 'audio/webm' }] },
      }),
    })
    const { container } = renderApp('/submissions/sub1')

    expect(await screen.findByRole('heading', { name: 'River story' })).toBeInTheDocument()
    expect(screen.getByText('Accepted')).toBeInTheDocument()
    expect(await screen.findByLabelText('Recording')).toBeInTheDocument()
    expect(container.querySelector('source')?.getAttribute('type')).toBe('audio/webm')

    const items = screen.getAllByRole('listitem').map((item) => item.textContent ?? '')
    expect(items[0]).toContain('यह एक परीक्षण वाक्य है।')
    expect(items[0]).toContain('version 2')
    expect(items[1]).toContain('Translation (English)')
    expect(items[1]).toContain('The text this translates has changed since')
    expect(screen.getAllByText('Written by the contributor, not checked by anyone')).toHaveLength(2)
  })

  it('says when the recording is not ready to play yet', async () => {
    fakeServer({
      'GET /auth/me': () => ({ body: SESSION }),
      'GET /submissions/sub1': () => ({ body: DETAIL }),
      'GET /recordings/rec1/playback': () => ({ body: { sources: [] } }),
    })
    renderApp('/submissions/sub1')
    expect(
      await screen.findByText('The recording is still being prepared for listening.'),
    ).toBeInTheDocument()
  })
})
