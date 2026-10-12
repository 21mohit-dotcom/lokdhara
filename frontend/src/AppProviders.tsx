import { useState, type ReactNode } from 'react'

import { AuthProvider, useAuth } from './auth/session'
import { DraftsProvider } from './drafts/DraftsProvider'
import { defaultDraftStore, type DraftStore } from './drafts/store'
import type { SyncApi } from './drafts/sync'

function Drafts({
  store,
  api,
  children,
}: {
  store: DraftStore
  api?: SyncApi
  children: ReactNode
}) {
  const { state } = useAuth()
  return (
    <DraftsProvider
      store={store}
      api={api}
      userId={state.status === 'signedIn' ? state.session.user.id : null}
    >
      {children}
    </DraftsProvider>
  )
}

export function AppProviders({
  store,
  api,
  children,
}: {
  store?: DraftStore
  api?: SyncApi
  children: ReactNode
}) {
  const [draftStore] = useState(() => store ?? defaultDraftStore())
  return (
    <AuthProvider>
      <Drafts store={draftStore} api={api}>
        {children}
      </Drafts>
    </AuthProvider>
  )
}
