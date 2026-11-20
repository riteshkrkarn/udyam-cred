import { forwardRef } from 'react'

const SignInDialog = forwardRef(function SignInDialog(_, ref) {
  function close() { ref.current?.close() }

  function handleSubmit(e) {
    e.preventDefault()
    close()
  }

  return (
    <dialog ref={ref}>
      <form onSubmit={handleSubmit}>
        <h3>Sign in</h3>
        <label>I am a
          <select name="role">
            <option>Shop owner</option>
            <option>Bank officer</option>
            <option>Approver</option>
            <option>Auditor</option>
          </select>
        </label>
        <p className="note">Demo only. No account is created.</p>
        <div className="actions">
          <button className="btn green" type="submit">Continue</button>
          <button type="button" className="btn small" onClick={close}>Cancel</button>
        </div>
      </form>
    </dialog>
  )
})

export default SignInDialog
