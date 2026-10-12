import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FormText } from './FormText'

describe('FormText', () => {
  it('shows headings and paragraphs as plain text, never as HTML', () => {
    const { container } = render(
      <FormText markdown={'# Title\n\n## Part two\n\n**Bold** text <b>not html</b>\n\nLast'} />,
    )
    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Part two' })).toBeInTheDocument()
    expect(screen.getByText('Bold text <b>not html</b>')).toBeInTheDocument()
    expect(container.querySelector('b')).toBeNull()
    expect(container.querySelectorAll('p')).toHaveLength(2)
  })
})
