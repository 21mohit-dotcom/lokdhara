import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// jsdom does not scroll; the wizard scrolls to the top on every step.
window.scrollTo = () => undefined

afterEach(() => cleanup())
