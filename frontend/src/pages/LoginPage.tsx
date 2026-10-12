import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { useAuth } from '../auth/session'
import { ErrorMessage } from '../components/ErrorMessage'

export function LoginPage() {
  const { t } = useTranslation()
  const { state, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  if (state.status === 'signedIn') return <Navigate to={from} replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(username, password)
      void navigate(from, { replace: true })
    } catch (failure) {
      setError(failure)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h1>{t('login.title')}</h1>
      <p className="note">{t('login.inviteOnly')}</p>
      <form className="form" onSubmit={(event) => void submit(event)}>
        <label>
          {t('login.username')}
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            required
          />
        </label>
        <label>
          {t('login.password')}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <ErrorMessage error={error} />
        <button type="submit" className="action primary" disabled={busy}>
          {t('login.submit')}
        </button>
      </form>
    </section>
  )
}
