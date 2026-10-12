import { useTranslation } from 'react-i18next'

import { errorCode } from '../api/client'

/** Shows the translation for an API error code, or a general message for unknown codes. */
export function ErrorMessage({ error }: { error: unknown }) {
  const { t, i18n } = useTranslation()
  if (!error) return null
  const code = typeof error === 'string' ? error : errorCode(error)
  const key = `errors.${code}`
  return (
    <p className="problem" role="alert">
      {i18n.exists(key) ? t(key) : t('errors.generic', { code })}
    </p>
  )
}
