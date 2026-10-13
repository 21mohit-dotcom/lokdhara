import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import * as api from '../api/endpoints'
import type { Job } from '../api/types'
import { hasRole, useSession } from '../auth/session'
import { ErrorMessage } from '../components/ErrorMessage'

/** Admins see the checks that failed for good and run them again (docs/ROADMAP.md M4). */
export function FailedJobsPage() {
  const { t, i18n } = useTranslation()
  const session = useSession()
  const isAdmin = hasRole(session, 'admin')
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [queued, setQueued] = useState<string[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    if (isAdmin) api.listFailedJobs().then(setJobs, setError)
  }, [isAdmin])

  if (!isAdmin) return <p className="note">{t('jobs.adminOnly')}</p>

  const retry = async (job: Job) => {
    setBusy(job.id)
    setError(null)
    try {
      await api.retryJob(job.id)
      setQueued((ids) => [...ids, job.id])
    } catch (caught) {
      setError(caught)
    } finally {
      setBusy(null)
    }
  }

  const date = (iso: string) => new Date(iso).toLocaleString(i18n.resolvedLanguage)

  return (
    <section>
      <h1>{t('jobs.title')}</h1>
      <p className="note">{t('jobs.intro')}</p>
      <ErrorMessage error={error} />
      {jobs?.length === 0 && <p className="note">{t('jobs.none')}</p>}
      <ul className="list">
        {jobs?.map((job) => (
          <li key={job.id} className="list-item">
            <strong>{job.job_type}</strong>
            <span>
              {job.target_type} {job.target_id}
            </span>
            <span>{t('jobs.error', { code: job.last_error_code ?? '?' })}</span>
            <span>{t('jobs.attempts', { attempts: job.attempts, max: job.max_attempts })}</span>
            {job.finished_at && <span>{t('jobs.finished', { date: date(job.finished_at) })}</span>}
            {queued.includes(job.id) ? (
              <span className="status waiting">{t('jobs.queued')}</span>
            ) : (
              <div className="row">
                <button
                  type="button"
                  className="small-action"
                  disabled={busy !== null}
                  onClick={() => void retry(job)}
                >
                  {t('jobs.retry')}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
