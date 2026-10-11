import { useTranslation } from 'react-i18next'

import { rememberLanguage, SUPPORTED_LANGUAGES, type LanguageCode } from '../i18n'

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation()

  const choose = (code: LanguageCode) => {
    rememberLanguage(code)
    void i18n.changeLanguage(code)
  }

  return (
    <div className="language-switcher" role="group" aria-label={t('nav.language')}>
      {SUPPORTED_LANGUAGES.map(({ code, label }) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={i18n.resolvedLanguage === code}
          onClick={() => choose(code)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
