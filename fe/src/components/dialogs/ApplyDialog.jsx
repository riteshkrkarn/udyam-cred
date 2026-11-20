import { forwardRef, useState } from 'react'

const ApplyDialog = forwardRef(function ApplyDialog(_, ref) {
  const [done, setDone] = useState(false)
  const [summary, setSummary] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const data = new FormData(e.target)
    const amount = Number(data.get('amount'))
    const purpose = data.get('purpose')
    setSummary(`Application for ₹${amount.toLocaleString('en-IN')} for "${purpose}" received. A loan officer will be in touch.`)
    setDone(true)
  }

  function close() {
    ref.current?.close()
    setTimeout(() => setDone(false), 300)
  }

  return (
    <dialog ref={ref}>
      {!done ? (
        <form id="apply-form" onSubmit={handleSubmit}>
          <h3>Apply for a loan</h3>
          <label>Amount needed (₹)
            <input type="number" name="amount" min="10000" step="1000" required />
          </label>
          <label>What is it for?
            <select name="purpose" required defaultValue="">
              <option value="" disabled>Choose one</option>
              <option>Stock purchase</option>
              <option>Festival stock</option>
              <option>Shop expansion</option>
              <option>Working capital</option>
              <option>Other</option>
            </select>
          </label>
          <label className="check">
            <input type="checkbox" name="consent" required />
            I agree to the use of my purchase bills, UPI and bank history and daily ledger for this assessment. I can withdraw consent at any time.
          </label>
          <div className="actions">
            <button className="btn red" type="submit">Submit application</button>
            <button type="button" className="btn small" onClick={close}>Cancel</button>
          </div>
        </form>
      ) : (
        <div>
          <h3>Application received</h3>
          <p>{summary}</p>
          <p className="note">Demo only. Nothing is sent or saved. Next, the owner would add purchase bills and ledger pages.</p>
          <button type="button" className="btn small" onClick={close}>Close</button>
        </div>
      )}
    </dialog>
  )
})

export default ApplyDialog
