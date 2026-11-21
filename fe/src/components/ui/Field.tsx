import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes } from 'react'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  note?: string
  error?: string
  /** Shows live value in the label (useful for range inputs) */
  outputValue?: string
  type?: string
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  note?: string
  error?: string
  options?: { value: string; label: string }[] | readonly { value: string; label: string }[]
}

const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, note, error, outputValue, type, ...inputProps },
  ref,
) {
  if (type === 'select') {
    return <span>Use SelectField instead</span>
  }

  return (
    <label>
      {label}
      {outputValue !== undefined && <output>{outputValue}</output>}
      <input ref={ref} type={type} {...inputProps} />
      {note && <span className="note">{note}</span>}
      {error && <span className="err">{error}</span>}
    </label>
  )
})

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(function SelectField(
  { label, note, error, options, ...selectProps },
  ref,
) {
  return (
    <label>
      {label}
      <select ref={ref} {...selectProps}>
        <option value="">Choose one</option>
        {options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {note && <span className="note">{note}</span>}
      {error && <span className="err">{error}</span>}
    </label>
  )
})

export default Field

// Range variant with live output built in
interface RangeFieldProps extends Omit<FieldProps, 'type'> {
  format?: (v: number) => string
}

export function RangeField({
  label,
  note,
  error,
  format,
  value,
  ...inputProps
}: RangeFieldProps) {
  const display = format && value !== undefined ? format(Number(value)) : String(value ?? '')
  return (
    <label>
      {label} <output>{display}</output>
      <input type="range" value={value} {...inputProps} />
      {note && <span className="note">{note}</span>}
      {error && <span className="err">{error}</span>}
    </label>
  )
}

// Checkbox variant
interface CheckFieldProps {
  label: string
  error?: string
  inputProps?: InputHTMLAttributes<HTMLInputElement>
}

export const CheckField = forwardRef<HTMLInputElement, CheckFieldProps & InputHTMLAttributes<HTMLInputElement>>(
  function CheckField({ label, error, ...inputProps }, ref) {
    return (
      <label className="check">
        <input type="checkbox" ref={ref} {...inputProps} />
        {label}
        {error && <span className="err">{error}</span>}
      </label>
    )
  },
)
