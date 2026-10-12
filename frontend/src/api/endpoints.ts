/** One function per API call the contributor app makes. */
import { request } from './client'
import type {
  ConsentAnswers,
  ConsentForm,
  Prompt,
  PromptType,
  Script,
  Session,
  Speaker,
  Submission,
  SubmissionCreate,
  TextLayer,
  TextLayerCreate,
} from './types'

export const login = (username: string, password: string) =>
  request<Session>('POST', '/auth/login', { json: { username, password } })
export const logout = () => request<void>('POST', '/auth/logout')
export const me = () => request<Session>('GET', '/auth/me')

export const listSpeakers = () =>
  request<{ items: Speaker[] }>('GET', '/speakers?mine=true').then((r) => r.items)
export const createSpeaker = (forSelf: boolean) =>
  request<Speaker>('POST', '/speakers', { json: { for_self: forSelf } })
export const getSpeaker = (id: string) => request<Speaker>('GET', `/speakers/${id}`)

export const currentConsentForm = (language: string) =>
  request<ConsentForm>('GET', `/consent-forms/current?language=${encodeURIComponent(language)}`)

export function recordConsent(speakerId: string, answers: ConsentAnswers, evidence?: Blob) {
  const form = new FormData()
  form.append('consent', JSON.stringify(answers))
  if (evidence) form.append('evidence', evidence, 'consent')
  return request<unknown>('POST', `/speakers/${speakerId}/consents`, { form })
}

export function nextPrompt(type: PromptType, script: Script | null, exclude: string[]) {
  const query = new URLSearchParams({ type })
  if (script) query.set('script', script)
  for (const id of exclude) query.append('exclude', id)
  return request<Prompt>('GET', `/prompts/next?${query}`)
}
export const getPrompt = (id: string) => request<Prompt>('GET', `/prompts/${id}`)

export const createSubmission = (body: SubmissionCreate) =>
  request<Submission>('POST', '/submissions', { json: body })
export const getSubmission = (id: string) => request<Submission>('GET', `/submissions/${id}`)
export const listSubmissions = () =>
  request<{ items: Submission[] }>('GET', '/submissions?mine=true&limit=100').then((r) => r.items)

export function uploadRecording(
  submissionId: string,
  audio: Blob,
  filename: string,
  source: 'browser_recorder' | 'file_upload',
  idempotencyKey: string,
) {
  const form = new FormData()
  form.append('file', audio, filename)
  form.append('source', source)
  return request<{ recording_id: string; upload_status: string }>(
    'POST',
    `/submissions/${submissionId}/recordings`,
    { form, headers: { 'Idempotency-Key': idempotencyKey } },
  )
}

export const createTextLayer = (submissionId: string, body: TextLayerCreate) =>
  request<TextLayer>('POST', `/submissions/${submissionId}/text-layers`, { json: body })

export const submitSubmission = (id: string) =>
  request<Submission>('POST', `/submissions/${id}/submit`)
