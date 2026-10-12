/** Drafts on the device. IndexedDB keeps audio Blobs across reloads and lost connections. */
import { createContext, useContext } from 'react'

import type { Draft } from './types'

export interface DraftStore {
  list(): Promise<Draft[]>
  get(id: string): Promise<Draft | undefined>
  put(draft: Draft): Promise<void>
  remove(id: string): Promise<void>
}

const DB_NAME = 'lokdhara'
const STORE = 'drafts'

function promised<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export function indexedDbDraftStore(): DraftStore {
  let opened: Promise<IDBDatabase> | null = null
  const db = () => {
    opened ??= new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1)
      req.onupgradeneeded = () => {
        req.result.createObjectStore(STORE, { keyPath: 'clientSubmissionId' })
      }
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => reject(req.error)
    })
    return opened
  }
  const store = async (mode: IDBTransactionMode) =>
    (await db()).transaction(STORE, mode).objectStore(STORE)

  return {
    async list() {
      const all = await promised((await store('readonly')).getAll() as IDBRequest<Draft[]>)
      return all.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    },
    async get(id) {
      return promised((await store('readonly')).get(id) as IDBRequest<Draft | undefined>)
    },
    async put(draft) {
      await promised((await store('readwrite')).put(draft))
    },
    async remove(id) {
      await promised((await store('readwrite')).delete(id))
    },
  }
}

/** For tests, and as a fallback when IndexedDB is unavailable. */
export function memoryDraftStore(): DraftStore {
  const drafts = new Map<string, Draft>()
  return {
    async list() {
      return [...drafts.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    },
    async get(id) {
      return drafts.get(id)
    },
    async put(draft) {
      drafts.set(draft.clientSubmissionId, draft)
    },
    async remove(id) {
      drafts.delete(id)
    },
  }
}

export function defaultDraftStore(): DraftStore {
  return typeof indexedDB === 'undefined' ? memoryDraftStore() : indexedDbDraftStore()
}

export const DraftStoreContext = createContext<DraftStore | null>(null)

export function useDraftStore(): DraftStore {
  const store = useContext(DraftStoreContext)
  if (!store) throw new Error('useDraftStore needs a DraftStoreContext provider')
  return store
}
