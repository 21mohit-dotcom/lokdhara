import { useTranslation } from 'react-i18next'

export function HomePage() {
  const { t } = useTranslation()
  return (
    <section className="home">
      <p className="tagline">{t('app.tagline')}</p>
      <div className="actions">
        {/* Real flows arrive in Milestone 3; buttons are placeholders. */}
        <button type="button" className="action primary" disabled>
          <span aria-hidden="true">🎙️</span> {t('home.newRecording')}
        </button>
        <button type="button" className="action" disabled>
          <span aria-hidden="true">📋</span> {t('home.mySubmissions')}
        </button>
      </div>
      <p className="note">{t('home.comingSoon')}</p>
    </section>
  )
}
