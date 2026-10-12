/**
 * Sends a ready draft to the server, step by step, saving progress on the device after each
 * step (docs/SYSTEM_ARCHITECTURE.md §4.1). Every step is safe to repeat: the draft ID, the
 * upload's Idempotency-Key, and the server's duplicate checks make a retry after a lost
 * response land on the same records instead of creating new ones.
 */
import { ApiError, errorCode } from '../api/client'
import * as endpoints from '../api/endpoints'
import type { SubmissionCreate, TextLayerCreate } from '../api/types'
import type { DraftStore } from './store'
import type { Draft, DraftText } from './types'

export type SyncApi = Pick<
  typeof endpoints,
  'createSubmission' | 'uploadRecording' | 'createTextLayer' | 'getSubmission' | 'submitSubmission'
>

export function submissionBody(draft: Draft): SubmissionCreate {
  const d = draft.details
  const optional = (value: string) => (value.trim() ? value.trim() : undefined)
  return {
    client_submission_id: draft.clientSubmissionId,
    speaker_id: draft.speakerId,
    kind: draft.kind,
    content_type: d.contentType,
    title: optional(d.title),
    dialect_label: optional(d.dialectLabel),
    region_coarse: optional(d.regionCoarse),
    recorded_on: optional(d.recordedOn),
    collection_method: draft.collectionMethod,
    recording_mode: draft.recordingMode,
    prompt_id: draft.promptId,
    collection_context: {
      setting: d.setting,
      speaker_count: d.speakerCount,
      equipment: d.equipment,
      notes: optional(d.notes),
    },
  }
}

/** Sources first, so a translation can name the layer it translates. */
function inOrder(texts: DraftText[]): DraftText[] {
  return [...texts.filter((t) => !t.translatesKey), ...texts.filter((t) => t.translatesKey)]
}

function layerBody(draft: Draft, text: DraftText): TextLayerCreate {
  const body: TextLayerCreate = {
    layer_type: text.layerType,
    language_tag: text.languageTag,
    script_code: text.scriptCode,
    content: text.content,
  }
  if (text.layerType === 'standalone') body.entry_type = text.entryType
  if (text.layerType === 'transcription') body.recording_id = draft.progress.recordingId
  if (text.translatesKey) {
    body.source_layer_id = draft.texts.find((t) => t.key === text.translatesKey)?.serverLayerId
  }
  return body
}

/** After a lost response the layer exists but its ID is unknown: find it on the server. */
async function findExistingLayer(api: SyncApi, submissionId: string, body: TextLayerCreate) {
  const submission = await api.getSubmission(submissionId)
  const match = submission.text_layers?.find((layer) =>
    body.layer_type === 'transcription'
      ? layer.recording_id === body.recording_id && layer.script_code === body.script_code
      : layer.source_layer_id === body.source_layer_id && layer.language_tag === body.language_tag,
  )
  if (!match) throw new ApiError(409, 'layer_exists')
  return match
}

export async function syncDraft(
  input: Draft,
  store: DraftStore,
  api: SyncApi = endpoints,
): Promise<void> {
  let draft = input
  const save = async (changes: Partial<Draft>) => {
    draft = { ...draft, ...changes, updatedAt: new Date().toISOString() }
    await store.put(draft)
  }

  try {
    let submissionId = draft.progress.submissionId
    if (!submissionId) {
      submissionId = (await api.createSubmission(submissionBody(draft))).id
      await save({ progress: { ...draft.progress, submissionId } })
    }

    if (draft.audio && !draft.progress.recordingId) {
      const { blob, filename, source } = draft.audio
      const uploaded = await api.uploadRecording(
        submissionId,
        blob,
        filename,
        source,
        draft.uploadKey,
      )
      await save({ progress: { ...draft.progress, recordingId: uploaded.recording_id } })
    }

    for (const text of inOrder(draft.texts)) {
      if (text.serverLayerId) continue
      const body = layerBody(draft, text)
      let layerId: string
      try {
        layerId = (await api.createTextLayer(submissionId, body)).id
      } catch (error) {
        if (!(error instanceof ApiError && error.code === 'layer_exists')) throw error
        layerId = (await findExistingLayer(api, submissionId, body)).id
      }
      await save({
        texts: draft.texts.map((t) => (t.key === text.key ? { ...t, serverLayerId: layerId } : t)),
      })
    }

    try {
      await api.submitSubmission(submissionId)
    } catch (error) {
      // Already submitted: an earlier attempt succeeded but its answer was lost.
      if (!(error instanceof ApiError && error.code === 'submission_not_draft')) throw error
    }
    // The server has everything now; do not keep the recording on a possibly shared phone.
    await store.remove(draft.clientSubmissionId)
  } catch (error) {
    await save({ lastError: errorCode(error) })
    throw error
  }
}
