/** A group of large radio buttons, easier to tap on a phone than a select. */
export function Choice<T extends string>({
  name,
  legend,
  options,
  value,
  onChange,
}: {
  name: string
  legend: string
  options: { value: T; label: string; hint?: string }[]
  value: T | undefined
  onChange: (value: T) => void
}) {
  return (
    <fieldset className="choice">
      <legend>{legend}</legend>
      {options.map((option) => (
        <label key={option.value} className="choice-option">
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span>
            {option.label}
            {option.hint && <small>{option.hint}</small>}
          </span>
        </label>
      ))}
    </fieldset>
  )
}
