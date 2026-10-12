import { useTranslation } from 'react-i18next'

import type { ContentType, Equipment, Setting } from '../../api/types'
import { Choice } from '../../components/Choice'
import type { DraftDetails } from '../../drafts/types'

const CONTENT_TYPES: ContentType[] = [
  'story',
  'conversation',
  'vocabulary',
  'song',
  'sentence_list',
  'other',
]
const SETTINGS: Setting[] = ['indoor_quiet', 'indoor_noisy', 'outdoor', 'unknown']
const EQUIPMENT: Equipment[] = [
  'phone_builtin_mic',
  'phone_external_mic',
  'field_recorder',
  'unknown',
]

/** Metadata as the contributor reports it (docs/DATA_DICTIONARY.md §3; FR-S5). */
export function DetailsStep({
  details,
  hasAudio,
  onChange,
}: {
  details: DraftDetails
  hasAudio: boolean
  onChange: (details: DraftDetails) => void
}) {
  const { t } = useTranslation()
  const set = (changes: Partial<DraftDetails>) => onChange({ ...details, ...changes })
  const today = new Date().toISOString().slice(0, 10)

  return (
    <div className="step">
      <Choice
        name="content-type"
        legend={t('details.contentType')}
        options={CONTENT_TYPES.map((value) => ({ value, label: t(`contentTypes.${value}`) }))}
        value={details.contentType}
        onChange={(contentType) => set({ contentType })}
      />
      <label>
        {t('details.title')}
        <input
          maxLength={200}
          value={details.title}
          onChange={(e) => set({ title: e.target.value })}
        />
      </label>
      <label>
        {t('details.dialect')}
        <input
          maxLength={100}
          value={details.dialectLabel}
          onChange={(e) => set({ dialectLabel: e.target.value })}
        />
      </label>
      <label>
        {t('details.region')}
        <input
          maxLength={100}
          value={details.regionCoarse}
          onChange={(e) => set({ regionCoarse: e.target.value })}
        />
        <small>{t('details.regionHint')}</small>
      </label>
      <label>
        {t('details.recordedOn')}
        <input
          type="date"
          max={today}
          value={details.recordedOn}
          onChange={(e) => set({ recordedOn: e.target.value })}
        />
      </label>
      {hasAudio && (
        <>
          <Choice
            name="setting"
            legend={t('details.setting')}
            options={SETTINGS.map((value) => ({ value, label: t(`settings.${value}`) }))}
            value={details.setting}
            onChange={(setting) => set({ setting })}
          />
          <Choice
            name="equipment"
            legend={t('details.equipment')}
            options={EQUIPMENT.map((value) => ({ value, label: t(`equipment.${value}`) }))}
            value={details.equipment}
            onChange={(equipment) => set({ equipment })}
          />
          <label>
            {t('details.speakerCount')}
            <input
              type="number"
              min={1}
              max={50}
              inputMode="numeric"
              value={details.speakerCount ?? ''}
              onChange={(e) =>
                set({ speakerCount: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </label>
        </>
      )}
      <label>
        {t('details.notes')}
        <textarea
          rows={3}
          maxLength={500}
          value={details.notes}
          onChange={(e) => set({ notes: e.target.value })}
        />
        <small>{t('details.notesHint')}</small>
      </label>
    </div>
  )
}
