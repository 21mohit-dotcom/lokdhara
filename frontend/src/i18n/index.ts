import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import hi from './locales/hi.json'

export const SUPPORTED_LANGUAGES = [
  { code: 'hi', label: 'हिन्दी' },
  { code: 'en', label: 'English' },
] as const

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]['code']

export const resources = { hi: { translation: hi }, en: { translation: en } } as const

const STORAGE_KEY = 'lkd.language'

function initialLanguage(): LanguageCode {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    if (saved === 'hi' || saved === 'en') return saved
  } catch {
    // Storage can be unavailable (private mode); fall back to Hindi.
  }
  return 'hi'
}

export function rememberLanguage(code: LanguageCode): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, code)
  } catch {
    // Not critical: the choice simply won't persist.
  }
}

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false }, // React already escapes output.
})

i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
})

export default i18n
