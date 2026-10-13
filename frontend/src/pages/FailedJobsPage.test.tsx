import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import i18n from '../i18n'
import { fakeServer, SESSION } from '../test/fakeServer'
import { renderApp } from '../test/render'

const ADMIN = { ...SESSION, roles: [{ role: 'admin', scope: null }] }
const JOB = {
  id: 'j1',
  job_type: 'audio.renditions',
  status: 'failed',
  attempts: 5,
  max_attempts: 5,
  target_type: 'recording',
  target_id: 'r1',
  last_error_code: 'ffmpeg_timeout',
  created_at: '2026-10-13T10:00:00Z',
  finished_at: '2026-10-13T11:00:00Z',
}

beforeEach(async () => {
  await i18n.changeLanguage('en')
})

describe('failed checks', () => {
  it('lets an admin run a failed check again', async () => {
    const { requests } = fakeServer({
      'GET /auth/me': () => ({ body: ADMIN }),
      'GET /admin/jobs\\?status=failed': () => ({ body: { items: [JOB] } }),
      'POST /admin/jobs/j1/retry': () => ({ body: { ...JOB, status: 'queued', attempts: 0 } }),
    })
    renderApp('/admin/jobs')

    expect(await screen.findByText('audio.renditions')).toBeInTheDocument()
    expect(screen.getByText('Error: ffmpeg_timeout')).toBeInTheDocument()
    expect(screen.getByText('Attempts: 5 of 5')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Run again' }))

    expect(await screen.findByText('Queued again')).toBeInTheDocument()
    expect(requests.filter((r) => r.method === 'POST').map((r) => r.path)).toEqual([
      '/admin/jobs/j1/retry',
    ])
  })

  it('says so when nothing failed', async () => {
    fakeServer({
      'GET /auth/me': () => ({ body: ADMIN }),
      'GET /admin/jobs\\?status=failed': () => ({ body: { items: [] } }),
    })
    renderApp('/admin/jobs')
    expect(await screen.findByText('No failed checks.')).toBeInTheDocument()
  })

  it('is only for admins, and only admins see the link', async () => {
    const { requests } = fakeServer({ 'GET /auth/me': () => ({ body: SESSION }) })
    renderApp('/admin/jobs')
    expect(await screen.findByText('Only admins can see this page.')).toBeInTheDocument()
    expect(requests.some((r) => r.path.startsWith('/admin'))).toBe(false)

    fakeServer({ 'GET /auth/me': () => ({ body: ADMIN }) })
    renderApp('/')
    expect(await screen.findByRole('link', { name: /Failed checks/ })).toBeInTheDocument()
  })
})
