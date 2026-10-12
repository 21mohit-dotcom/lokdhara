import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { DraftAudio } from '../drafts/types'
import {
  canRecord,
  extensionFor,
  MIN_RECORDING_MS,
  startRecording,
  type ActiveRecording,
} from './recorder'

const FILE_TYPES = 'audio/*,.aac,.m4a,.mp3,.wav,.flac,.ogg,.opus,.webm'

/** Record in the browser or choose a file; shows a player for what was captured. */
export function AudioCapture({
  value,
  onChange,
  allowFile = true,
}: {
  value: DraftAudio | undefined
  onChange: (audio: DraftAudio | undefined) => void
  allowFile?: boolean
}) {
  const { t } = useTranslation()
  const [active, setActive] = useState<ActiveRecording | null>(null)
  const [seconds, setSeconds] = useState(0)
  const [problem, setProblem] = useState<string | null>(null)
  const ticker = useRef<number | undefined>(undefined)

  const url = useMemo(() => (value ? URL.createObjectURL(value.blob) : null), [value])
  useEffect(() => () => (url ? URL.revokeObjectURL(url) : undefined), [url])

  useEffect(() => () => window.clearInterval(ticker.current), [])
  useEffect(() => () => active?.cancel(), [active])

  const start = async () => {
    setProblem(null)
    try {
      const recording = await startRecording()
      setSeconds(0)
      ticker.current = window.setInterval(() => setSeconds((s) => s + 1), 1000)
      setActive(recording)
    } catch {
      setProblem('record.noMicrophone')
    }
  }

  const stop = async () => {
    if (!active) return
    window.clearInterval(ticker.current)
    const { blob, durationMs, mimeType } = await active.stop()
    setActive(null)
    if (durationMs < MIN_RECORDING_MS) {
      setProblem('record.tooShort')
      return
    }
    onChange({ blob, filename: `recording.${extensionFor(mimeType)}`, source: 'browser_recorder' })
  }

  const choose = (file: File | undefined) => {
    setProblem(null)
    if (file) onChange({ blob: file, filename: file.name, source: 'file_upload' })
  }

  const time = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`

  return (
    <div className="capture">
      {active ? (
        <div className="recording-now" role="status">
          <span className="dot" aria-hidden="true" /> {t('record.recording')} {time}
          <button type="button" className="action primary" onClick={() => void stop()}>
            {t('record.stop')}
          </button>
        </div>
      ) : (
        <div className="actions">
          {canRecord() && (
            <button type="button" className="action primary" onClick={() => void start()}>
              <span aria-hidden="true">🎙️</span> {value ? t('record.again') : t('record.start')}
            </button>
          )}
          {allowFile && (
            <label className="action file-choice">
              <span aria-hidden="true">📁</span> {t('record.chooseFile')}
              <input
                type="file"
                accept={FILE_TYPES}
                onChange={(event) => choose(event.target.files?.[0])}
              />
            </label>
          )}
        </div>
      )}
      {problem && (
        <p className="problem" role="alert">
          {t(problem)}
        </p>
      )}
      {value && url && !active && (
        <div className="captured">
          <p>{t('record.ready')}</p>
          <audio controls src={url} aria-label={t('record.listen')} />
        </div>
      )}
    </div>
  )
}
