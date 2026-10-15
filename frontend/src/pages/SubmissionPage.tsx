import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'

import * as api from '../api/endpoints'
import type { Playback, Recording, SubmissionDetail, TextLayerDetail } from '../api/types'
import { ErrorMessage } from '../components/ErrorMessage'

/** One sent submission: its status, its recording to listen to, and its texts (ROADMAP M5). */
export function SubmissionPage() {
  const { t, i18n } = useTranslation()
  const { submissionId = '' } = useParams()
  const [submission, setSubmission] = useState<SubmissionDetail | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    api.getSubmissionDetail(submissionId).then(setSubmission, setError)
  }, [submissionId])

  if (!submission) return <ErrorMessage error={error} />

  const date = (iso: string) => new Date(iso).toLocaleDateString(i18n.resolvedLanguage)
  // Each text, with the translations of it right after it.
  const sources = submission.text_layers.filter((layer) => !layer.source_layer_id)
  const ordered = sources.flatMap((source) => [
    source,
    ...submission.text_layers.filter((layer) => layer.source_layer_id === source.id),
  ])

  return (
    <section>
      <p>
        <Link to="/submissions">{t('submission.back')}</Link>
      </p>
      <h1>{submission.title || t(`kinds.${submission.kind}`)}</h1>
      <span className={`status status-${submission.status}`}>
        {t(`statuses.${submission.status}`, { defaultValue: submission.status })}
      </span>
      <p className="note">
        {t('submission.sentOn', { date: date(submission.submitted_at ?? submission.created_at) })}
      </p>
      <ErrorMessage error={error} />

      {submission.recordings.map((recording) => (
        <RecordingPlayer key={recording.id} recording={recording} />
      ))}

      <h2>{t('submission.texts')}</h2>
      {ordered.length === 0 && <p className="note">{t('submission.noText')}</p>}
      <ul className="list">
        {ordered.map((layer) => (
          <TextLayerItem key={layer.id} layer={layer} />
        ))}
      </ul>
    </section>
  )
}

function RecordingPlayer({ recording }: { recording: Recording }) {
  const { t } = useTranslation()
  const [playback, setPlayback] = useState<Playback | null>(null)
  const usable = recording.upload_status === 'promoted'

  useEffect(() => {
    if (usable) api.getPlayback(recording.id).then(setPlayback, () => setPlayback(null))
  }, [recording.id, usable])

  return (
    <>
      <h2>{t('submission.recording')}</h2>
      {playback && playback.sources.length > 0 ? (
        <audio controls preload="none" aria-label={t('submission.recording')}>
          {playback.sources.map((source) => (
            <source key={source.url} src={source.url} type={source.content_type} />
          ))}
        </audio>
      ) : (
        <p className="note">
          {usable ? t('submission.notReadyToPlay') : t('submission.notPlayable')}
        </p>
      )}
    </>
  )
}

function TextLayerItem({ layer }: { layer: TextLayerDetail }) {
  const { t } = useTranslation()
  const revision = layer.current_revision
  return (
    <li className="list-item">
      <strong>
        {t(`review.text.${layer.layer_type}`, {
          language: t(`submission.languages.${layer.language_tag}`, {
            defaultValue: layer.language_tag,
          }),
        })}
      </strong>
      <span className="note">
        {t(`scripts.${layer.script_code}`, { defaultValue: layer.script_code })}
        {revision && ` · ${t('submission.version', { number: revision.revision_number })}`}
      </span>
      {revision && (
        <p className="user-text" lang={layer.language_tag}>
          {revision.content}
        </p>
      )}
      {revision?.verification_status !== 'verified' && (
        <span className="badge">{t('submission.unverified')}</span>
      )}
      {layer.source_changed && (
        <span className="status waiting">{t('submission.sourceChanged')}</span>
      )}
    </li>
  )
}
