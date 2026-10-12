import { useTranslation } from 'react-i18next'

import { useSession } from '../auth/session'

export function HomePage() {
  const { t } = useTranslation()
  const session = useSession()
  return (
    <section className="home">
      <p className="tagline">{t('home.greeting', { name: session.user.display_name })}</p>
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
