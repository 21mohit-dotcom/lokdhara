/**
 * Keeps the list of drafts on this device and uploads the ready ones in the background:
 * on sign-in, when the connection comes back, when a draft is finished, and after a delay
 * when a temporary failure (offline, server busy) stopped an upload.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import { isRetryable } from '../api/client'
import { DraftStoreContext, type DraftStore } from './store'
import { syncDraft, type SyncApi } from './sync'
import type { Draft } from './types'

const RETRY_DELAYS_MS = [10_000, 30_000, 60_000, 300_000]

interface Drafts {
  drafts: Draft[]
  uploading: boolean
  refresh: () => Promise<void>
  uploadNow: () => void
}

const DraftsContext = createContext<Drafts | null>(null)

export function DraftsProvider({
  store,
  api,
  userId,
  children,
}: {
  store: DraftStore
  api?: SyncApi
  /** The signed-in user; only their drafts are listed and uploaded. */
  userId: string | null
  children: ReactNode
}) {
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [uploading, setUploading] = useState(false)
  const running = useRef(false)
  const again = useRef(false)
  const attempt = useRef(0)
  const timer = useRef<number | undefined>(undefined)
  const runAgain = useRef<() => void>(() => undefined)

  const own = useCallback(
    async () => (await store.list()).filter((draft) => draft.ownerId === userId),
    [store, userId],
  )
  const refresh = useCallback(async () => setDrafts(await own()), [own])

  const run = useCallback(async () => {
    if (!userId) return
    if (running.current) {
      again.current = true // a draft became ready during this run
      return
    }
    running.current = true
    again.current = false
    window.clearTimeout(timer.current)
    let retryLater = false
    try {
      const drafts = await own()
      setUploading(true)
      for (const draft of drafts) {
        if (!draft.ready) continue
        try {
          await syncDraft(draft, store, api)
        } catch (error) {
          if (isRetryable(error)) {
            retryLater = true
            break // probably offline: the rest would fail the same way
          }
        }
      }
    } finally {
      running.current = false
      setUploading(false)
      await refresh()
    }
    if (again.current) {
      runAgain.current()
    } else if (retryLater) {
      const delay = RETRY_DELAYS_MS[Math.min(attempt.current, RETRY_DELAYS_MS.length - 1)]
      attempt.current += 1
      timer.current = window.setTimeout(() => runAgain.current(), delay)
    } else {
      attempt.current = 0
    }
  }, [api, own, refresh, store, userId])

  useEffect(() => {
    runAgain.current = () => void run()
  }, [run])

  useEffect(() => {
    let live = true
    void own().then((list) => live && setDrafts(list))
    return () => {
      live = false
    }
  }, [own])

  useEffect(() => {
    void run()
    const online = () => {
      attempt.current = 0
      void run()
    }
    window.addEventListener('online', online)
    return () => {
      window.removeEventListener('online', online)
      window.clearTimeout(timer.current)
    }
  }, [run])

  const uploadNow = useCallback(() => {
    attempt.current = 0
    void run()
  }, [run])

  const value = useMemo(
    () => ({ drafts, uploading, refresh, uploadNow }),
    [drafts, uploading, refresh, uploadNow],
  )
  return (
    <DraftStoreContext.Provider value={store}>
      <DraftsContext.Provider value={value}>{children}</DraftsContext.Provider>
    </DraftStoreContext.Provider>
  )
}

export function useDrafts(): Drafts {
  const drafts = useContext(DraftsContext)
  if (!drafts) throw new Error('useDrafts needs a DraftsProvider')
  return drafts
}
