import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'

import { AppProviders } from '../AppProviders'
import { memoryDraftStore, type DraftStore } from '../drafts/store'
import { routes } from '../routes'

export function renderApp(path: string, store: DraftStore = memoryDraftStore()) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const view = render(
    <AppProviders store={store}>
      <RouterProvider router={router} />
    </AppProviders>,
  )
  return { ...view, router, store }
}
