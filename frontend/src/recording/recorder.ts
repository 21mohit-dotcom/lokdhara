/** Browser recording (docs/AUDIO_PROCESSING_PIPELINE.md §4): no transcoding on the phone. */

// Chrome and Firefox record Opus in WebM; Safari only records MP4/AAC.
const PREFERRED_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4',
  'audio/ogg;codecs=opus',
]

export function pickMimeType(isSupported: (type: string) => boolean): string | undefined {
  return PREFERRED_TYPES.find((type) => isSupported(type))
}

export function extensionFor(mimeType: string): string {
  if (mimeType.startsWith('audio/mp4')) return 'm4a'
  if (mimeType.startsWith('audio/ogg')) return 'ogg'
  return 'webm'
}

export const MIN_RECORDING_MS = 1000

export function canRecord(): boolean {
  return typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getUserMedia
}

export interface ActiveRecording {
  stop: () => Promise<{ blob: Blob; durationMs: number; mimeType: string }>
  cancel: () => void
}

export async function startRecording(): Promise<ActiveRecording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const mimeType = pickMimeType((type) => MediaRecorder.isTypeSupported(type))
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
  const chunks: Blob[] = []
  const started = performance.now()
  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) chunks.push(event.data)
  }
  // Data arrives in one-second pieces; they are joined into one file on stop.
  recorder.start(1000)
  const release = () => stream.getTracks().forEach((track) => track.stop())

  return {
    stop: () =>
      new Promise((resolve) => {
        recorder.onstop = () => {
          release()
          const type = recorder.mimeType || mimeType || 'audio/webm'
          resolve({
            blob: new Blob(chunks, { type }),
            durationMs: performance.now() - started,
            mimeType: type,
          })
        }
        recorder.stop()
      }),
    cancel: () => {
      if (recorder.state === 'inactive') return release()
      recorder.onstop = release
      recorder.stop()
    },
  }
}
