/** Shapes of the API's JSON (docs/API_SPECIFICATION.md). Only the fields the app uses. */

export type Role = 'contributor' | 'facilitator' | 'reviewer' | 'researcher' | 'admin'

export interface Session {
  user: { id: string; username: string; display_name: string; preferred_locale: string }
  roles: { role: Role; scope: string | null }[]
  csrf_token: string
}

export interface Speaker {
  id: string
  speaker_code: string
  is_self: boolean
  status: string
  has_active_consent: boolean
  dialect_label: string | null
}

export interface ConsentForm {
  id: string
  version: string
  language: string
  body_markdown: string
  is_test_form: boolean
}

export type ConsentMethod = 'in_app' | 'oral_recorded' | 'paper_reference'
export type Attribution = 'pseudonymous' | 'name' | 'none'

export interface ConsentAnswers {
  consent_form_id: string
  method: ConsentMethod
  paper_reference?: string
  allow_store_and_review: boolean
  allow_research: boolean
  allow_public_access: boolean
  allow_ai_training: boolean
  allow_commercial_use: boolean
  attribution_preference: Attribution
  demographics_consented: boolean
}

export type PromptType = 'image' | 'situation' | 'read_sentence'
export type Script = 'Deva' | 'Latn' | 'Nagm' | 'Beng' | 'Orya' | 'Zyyy'

export interface Prompt {
  id: string
  prompt_type: PromptType
  text: string | null
  text_language_tag: string | null
  script_code: Script | null
  image_url: string | null
  audio_url: string | null
}

export type Kind = 'audio' | 'text' | 'audio_text'
export type RecordingMode = 'free' | 'prompted' | 'read'
export type ContentType =
  | 'story'
  | 'conversation'
  | 'vocabulary'
  | 'song'
  | 'sentence_list'
  | 'other'
export type CollectionMethod = 'self_recorded' | 'facilitator_field' | 'facilitator_remote'
export type LayerType = 'standalone' | 'transcription' | 'translation'
export type EntryType = 'word' | 'phrase' | 'sentence' | 'paragraph' | 'long_text'
export type Setting = 'indoor_quiet' | 'indoor_noisy' | 'outdoor' | 'unknown'
export type Equipment = 'phone_builtin_mic' | 'phone_external_mic' | 'field_recorder' | 'unknown'

export interface CollectionContext {
  setting?: Setting
  speaker_count?: number
  equipment?: Equipment
  notes?: string
}

export interface SubmissionCreate {
  client_submission_id: string
  speaker_id: string
  kind: Kind
  content_type: ContentType
  title?: string
  dialect_label?: string
  region_coarse?: string
  recorded_on?: string
  collection_method: CollectionMethod
  recording_mode?: RecordingMode
  prompt_id?: string
  collection_context: CollectionContext
}

export interface TextLayer {
  id: string
  layer_type: LayerType
  recording_id: string | null
  source_layer_id: string | null
  language_tag: string
  script_code: Script
}

export interface Submission {
  id: string
  client_submission_id: string
  kind: Kind
  content_type: ContentType
  title: string | null
  status: string
  recording_mode: RecordingMode | null
  created_at: string
  submitted_at: string | null
  text_layers?: TextLayer[]
}

export interface TextLayerCreate {
  layer_type: LayerType
  recording_id?: string
  source_layer_id?: string
  entry_type?: EntryType
  language_tag: string
  script_code: Script
  content: string
}
