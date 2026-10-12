import type { ReactNode } from 'react'
import type { RouteObject } from 'react-router'

import { RequireAuth } from './auth/session'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { NotFoundPage } from './pages/NotFoundPage'

const signedIn = (page: ReactNode) => <RequireAuth>{page}</RequireAuth>

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: signedIn(<HomePage />) },
      { path: 'login', element: <LoginPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
