import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useApplyStore, type ApplyFormValues } from './applyStore'
import Sheet from '../../components/ui/Sheet'

const schema = z.object({
  amount: z
    .number()
    .min(10_000, 'Minimum loan amount is ₹10,000.')
    .max(2_000_000, 'Maximum loan amount is ₹20,00,000.'),
  purpose: z.enum([
    'Stock purchase',
    'Festival stock',
    'Shop expansion',
    'Working capital',
    'Other',
  ]),
  consent: z.literal(true),
})

type FormValues = z.infer<typeof schema>

const PURPOSES = [
  'Stock purchase',
  'Festival stock',
  'Shop expansion',
  'Working capital',
  'Other',
] as const

export default function ApplyPage() {
  const navigate = useNavigate()
  const submit = useApplyStore((s) => s.submit)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  function onSubmit(values: FormValues) {
    const id = submit(values as ApplyFormValues)
    navigate(`/applications/${id}/result`)
  }

  return (
    <div style={{ maxWidth: 480, padding: '3rem 0' }}>
      <p className="eyebrow">Apply</p>
      <h1 style={{ fontSize: 'clamp(1.5rem, 3vw, 2rem)', marginBottom: '0.5rem' }}>
        Apply for a loan
      </h1>
      <p className="sub" style={{ marginBottom: '2rem' }}>
        Tell us how much you need and what it is for. The assessment uses your stock, bills and UPI
        history — no traditional credit score.
      </p>

      <Sheet>
        <p className="note" style={{ marginBottom: '1rem' }}>
          Demo only. No data leaves this browser.
        </p>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <label>
            Amount needed (₹)
            <input
              type="number"
              min={10_000}
              step={1_000}
              placeholder="e.g. 200000"
              {...register('amount', { valueAsNumber: true })}
            />
            {errors.amount && <span className="err">{errors.amount.message}</span>}
          </label>

          <label>
            What is it for?
            <select defaultValue="" {...register('purpose')}>
              <option value="" disabled>
                Choose one
              </option>
              {PURPOSES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            {errors.purpose && <span className="err">{errors.purpose.message}</span>}
          </label>

          <label className="check" style={{ marginTop: '1rem', marginBottom: '0.5rem' }}>
            <input type="checkbox" {...register('consent')} />I agree to the use of my purchase
            bills, UPI and bank history and daily ledger for this assessment. I can withdraw consent
            at any time.
          </label>
          {errors.consent && <span className="err">{errors.consent.message}</span>}

          <div className="actions" style={{ marginTop: '1.5rem' }}>
            <button className="btn red" type="submit">
              Submit application
            </button>
            <button
              type="button"
              className="btn small"
              onClick={() => navigate('/')}
            >
              Cancel
            </button>
          </div>
        </form>
      </Sheet>
    </div>
  )
}
