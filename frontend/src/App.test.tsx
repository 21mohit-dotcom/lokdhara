import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import i18n from './i18n'
import { routes } from './routes'

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(<RouterProvider router={router} />)
}

describe('app shell', () => {
  beforeEach(async () => {
    window.localStorage.clear()
    await i18n.changeLanguage('hi')
  })

  it('opens in Hindi by default with the two main actions', () => {
    renderAt('/')
    expect(screen.getByRole('button', { name: /नई रिकॉर्डिंग/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /मेरी प्रविष्टियाँ/ })).toBeInTheDocument()
  })

  it('switches to English and remembers the choice', async () => {
    renderAt('/')
    await userEvent.click(screen.getByRole('button', { name: 'English' }))
    expect(screen.getByRole('button', { name: /New recording/ })).toBeInTheDocument()
    expect(window.localStorage.getItem('lkd.language')).toBe('en')
    expect(document.documentElement.lang).toBe('en')
  })

  it('shows a not-found page for unknown routes', () => {
    renderAt('/does-not-exist')
    expect(screen.getByRole('heading', { name: 'पेज नहीं मिला' })).toBeInTheDocument()
  })
})
