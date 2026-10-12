import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router'

import { useAuth } from '../auth/session'
import { LanguageSwitcher } from './LanguageSwitcher'

export function Layout() {
  const { t } = useTranslation()
  const { state, signOut } = useAuth()
  return (
    <div className="layout">
      <header className="header">
        <Link to="/" className="brand">
          {t('app.name')}
        </Link>
        <div className="header-tools">
          <LanguageSwitcher />
          {state.status === 'signedIn' && (
            <button type="button" className="link-button" onClick={() => void signOut()}>
              {t('nav.signOut')}
            </button>
          )}
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
