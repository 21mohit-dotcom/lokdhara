/**
 * Shows a consent form's Markdown as plain text: headings and paragraphs only, with emphasis
 * markers removed. Nothing in it is ever interpreted as HTML.
 */
export function FormText({ markdown }: { markdown: string }) {
  const blocks = markdown
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean)
  return (
    <div className="form-text">
      {blocks.map((block, index) => {
        const text = block.replace(/\*\*/g, '')
        const heading = /^#{1,6} (.*)$/s.exec(text)
        return heading ? <h2 key={index}>{heading[1]}</h2> : <p key={index}>{text}</p>
      })}
    </div>
  )
}
