import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import i18n from '../i18n'
import { memoryDraftStore } from '../drafts/store'
import { emptyDetails, type Draft } from '../drafts/types'
import { fakeServer, SESSION, SPEAKER } from '../test/fakeServer'
import { renderApp } from '../test/render'
import { safeNext } from './ConsentPage'

const FORM = {
  id: 'f1',
  version: 'test-1',
  language: 'en',
  body_markdown: '# About the project\n\nThis is a **test** form.',
  is_test_form: true,
}

beforeEach(async () => {
  await i18n.changeLanguage('en')
})
afterEach(() => vi.unstubAllGlobals())

describe('consent', () => {
  it('starts every answer at No and needs permission to keep the recording', async () => {
    const { requests } = fakeServer({
      'GET /auth/me': () => ({ body: SESSION }),
      'GET /speakers/s1': () => ({ body: { ...SPEAKER, has_active_consent: false } }),
      'GET /consent-forms/current.*': () => ({ body: FORM }),
      'POST /speakers/s1/consents': () => ({ status: 201, body: {} }),
    })
    const { router } = renderApp('/speakers/s1/consent?next=/contribute')

    expect(await screen.findByText(/Test form/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'About the project' })).toBeInTheDocument()
    const groups = screen.getAllByRole('group').filter((g) => g.tagName === 'FIELDSET')
    for (const group of groups.slice(0, 6)) {
      expect(within(group).getByRole('radio', { name: 'No' })).toBeChecked()
    }
    const save = screen.getByRole('button', { name: 'Save consent' })
    expect(save).toBeDisabled()

    await userEvent.click(within(groups[0]!).getByRole('radio', { name: 'Yes' }))
    await userEvent.click(save)
    await waitFor(() => expect(router.state.location.pathname).toBe('/contribute'))

    const sent = requests.find((r) => r.method === 'POST')?.body as FormData
    expect(JSON.parse(String(sent.get('consent')))).toMatchObject({
      consent_form_id: 'f1',
      method: 'in_app',
      allow_store_and_review: true,
      allow_research: false,
      allow_public_access: false,
      allow_ai_training: false,
      allow_commercial_use: false,
      attribution_preference: 'pseudonymous',
    })
  })
})

describe('safeNext', () => {
  it('only returns to pages of this site', () => {
    expect(safeNext('/contribute/s1/new')).toBe('/contribute/s1/new')
    expect(safeNext('//evil.example/x')).toBe('/')
    expect(safeNext('https://evil.example')).toBe('/')
    expect(safeNext(null)).toBe('/')
  })
})

describe('my submissions', () => {
  it("does not show or upload another person's drafts on a shared phone", async () => {
    const { requests } = fakeServer({
      'GET /auth/me': () => ({ body: SESSION }),
      'GET /submissions\\?.*': () => ({ body: { items: [] } }),
    })
    const store = memoryDraftStore()
    const theirs: Draft = {
      clientSubmissionId: 'c2',
      ownerId: 'someone-else',
      speakerId: 's9',
      speakerCode: 'SPK-OTHER1',
      collectionMethod: 'self_recorded',
      kind: 'text',
      texts: [
        {
          key: 'main',
          layerType: 'standalone',
          entryType: 'word',
          languageTag: 'unr',
          scriptCode: 'Deva',
          content: 'क',
        },
      ],
      details: { ...emptyDetails(), title: 'Not yours' },
      uploadKey: 'k2',
      ready: true,
      progress: {},
      createdAt: '2026-10-12T00:00:00Z',
      updatedAt: '2026-10-12T00:00:00Z',
    }
    await store.put(theirs)
    renderApp('/submissions', store)

    expect(await screen.findByText('Nothing sent yet.')).toBeInTheDocument()
    expect(screen.queryByText('Not yours')).not.toBeInTheDocument()
    expect(requests.some((r) => r.method === 'POST')).toBe(false)
  })
})
