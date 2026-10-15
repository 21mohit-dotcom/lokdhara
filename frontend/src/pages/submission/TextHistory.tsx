import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import * as api from '../../api/endpoints'
import type { DiffPart, Revision } from '../../api/types'
import { ErrorMessage } from '../../components/ErrorMessage'

/** Every saved version of a text, newest first; each one can show what it changed. */
export function TextHistory({ layerId, language }: { layerId: string; language: string }) {
  const { t } = useTranslation()
  const [revisions, setRevisions] = useState<Revision[] | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    api.listRevisions(layerId).then((list) => setRevisions(list.items), setError)
  }, [layerId])

  if (!revisions) return <ErrorMessage error={error} />
  return (
    <ol className="history" aria-label={t('submission.history.title')}>
      {revisions.map((revision) => (
        <HistoryEntry key={revision.id} revision={revision} language={language} />
      ))}
    </ol>
  )
}

function HistoryEntry({ revision, language }: { revision: Revision; language: string }) {
  const { t, i18n } = useTranslation()
  const [parts, setParts] = useState<DiffPart[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const date = new Date(revision.created_at).toLocaleString(i18n.resolvedLanguage)
  const earlier = revision.based_on_revision_id

  const showChanges = () => {
    if (!earlier) return
    api.diffRevisions(earlier, revision.id).then((diff) => setParts(diff.parts), setError)
  }

  return (
    <li>
      <strong>{t('submission.version', { number: revision.revision_number })}</strong>
      <span className="note">
        {' · '}
        {date}
        {revision.change_note && ` · ${revision.change_note}`}
      </span>
      {parts ? (
        <p className="user-text" lang={language}>
          {parts.map((part, index) =>
            part.op === 'insert' ? (
              <ins key={index}>{part.text}</ins>
            ) : part.op === 'delete' ? (
              <del key={index}>{part.text}</del>
            ) : (
              <span key={index}>{part.text}</span>
            ),
          )}
        </p>
      ) : (
        <p className="user-text" lang={language}>
          {revision.content}
        </p>
      )}
      <ErrorMessage error={error} />
      {earlier && !parts && (
        <button type="button" className="small-action" onClick={showChanges}>
          {t('submission.history.showChanges')}
        </button>
      )}
    </li>
  )
}
