import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { useSession } from '../auth/session'
import { useDrafts } from '../drafts/DraftsProvider'

export function HomePage() {
  const { t } = useTranslation()
  const session = useSession()
  const { drafts } = useDrafts()
  const waiting = drafts.length

  return (
    <section className="home">
      <p className="tagline">{t('home.greeting', { name: session.user.display_name })}</p>
      <div className="actions">
        <Link to="/contribute" className="action primary">
          <span aria-hidden="true">🎙️</span> {t('home.newRecording')}
        </Link>
        <Link to="/submissions" className="action">
          <span aria-hidden="true">📋</span> {t('home.mySubmissions')}
          {waiting > 0 && <span className="badge">{t('home.onDevice', { count: waiting })}</span>}
        </Link>
      </div>
    </section>
  )
}
