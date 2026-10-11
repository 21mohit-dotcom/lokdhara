import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router'

import { LanguageSwitcher } from './LanguageSwitcher'

export function Layout() {
  const { t } = useTranslation()
  return (
    <div className="layout">
      <header className="header">
        <Link to="/" className="brand">
          {t('app.name')}
        </Link>
        <LanguageSwitcher />
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
