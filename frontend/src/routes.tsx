import type { ReactNode } from 'react'
import type { RouteObject } from 'react-router'

import { RequireAuth } from './auth/session'
import { Layout } from './components/Layout'
import { ChooseSpeakerPage } from './pages/ChooseSpeakerPage'
import { ConsentPage } from './pages/ConsentPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { MySubmissionsPage } from './pages/MySubmissionsPage'
import { NotFoundPage } from './pages/NotFoundPage'

const signedIn = (page: ReactNode) => <RequireAuth>{page}</RequireAuth>

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: signedIn(<HomePage />) },
      { path: 'login', element: <LoginPage /> },
      { path: 'contribute', element: signedIn(<ChooseSpeakerPage />) },
      { path: 'speakers/:speakerId/consent', element: signedIn(<ConsentPage />) },
      { path: 'submissions', element: signedIn(<MySubmissionsPage />) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
