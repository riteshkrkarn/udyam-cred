import { useState } from 'react'
import Modal from '../../components/ui/Modal'
import { useAuthStore, getCurrentRole, type Role } from './authStore'
import { useLogin } from '../../api/queries'

const DEMO_ROLES: { value: Role; label: string }[] = [
  { value: 'borrower', label: 'Shop owner' },
  { value: 'officer', label: 'Bank officer' },
  { value: 'approver', label: 'Approver' },
  { value: 'auditor', label: 'Auditor' },
]

interface Props {
  open: boolean
  onClose: () => void
}

export default function SignInDialog({ open, onClose }: Props) {
  const { setDemoRole, user, useDemo } = useAuthStore()
  const login = useLogin()
  const [mode, setMode] = useState<'demo' | 'login'>('demo')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [error, setError] = useState('')

  function handleDemoRole(role: Role) {
    setDemoRole(role)
    onClose()
  }

  async function handleRealLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await login.mutateAsync({ email, password, remember_me: rememberMe })
      onClose()
    } catch (err: any) {
      setError(err.detail || 'Login failed')
    }
  }

  return (
    <Modal open={open} onClose={onClose}>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', borderBottom: '1px solid var(--rule)', paddingBottom: '1rem' }}>
        <button
          type="button"
          onClick={() => setMode('demo')}
          style={{
            background: mode === 'demo' ? 'var(--green)' : 'transparent',
            color: mode === 'demo' ? 'var(--sheet)' : 'var(--ink)',
            border: 'none',
            cursor: 'pointer',
            padding: '0.5rem 1rem',
            borderRadius: 4,
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          Demo
        </button>
        <button
          type="button"
          onClick={() => setMode('login')}
          style={{
            background: mode === 'login' ? 'var(--green)' : 'transparent',
            color: mode === 'login' ? 'var(--sheet)' : 'var(--ink)',
            border: 'none',
            cursor: 'pointer',
            padding: '0.5rem 1rem',
            borderRadius: 4,
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          Real auth
        </button>
      </div>

      {mode === 'demo' ? (
        <div>
          <h3>Demo mode</h3>
          <p className="note" style={{ marginBottom: '1rem' }}>
            Choose a role. You're now in demo mode — no account needed.
          </p>
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {DEMO_ROLES.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => handleDemoRole(o.value)}
                style={{
                  padding: '0.75rem 1rem',
                  border: '1px solid var(--rule)',
                  borderRadius: 4,
                  background: 'var(--sheet)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: 14,
                }}
              >
                {o.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="btn small"
            onClick={onClose}
            style={{ marginTop: '1rem' }}
          >
            Cancel
          </button>
        </div>
      ) : (
        <form onSubmit={handleRealLogin}>
          <h3>Sign in</h3>
          <p className="note" style={{ marginBottom: '1rem' }}>
            Log in with your account. (Backend required at localhost:8000)
          </p>

          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <label className="check">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            Remember me (30 days)
          </label>

          {error && <p className="err">{error}</p>}
          {login.isError && <p className="err">{(login.error as any)?.detail || 'Login failed'}</p>}

          <div className="actions">
            <button className="btn green" type="submit" disabled={login.isPending}>
              {login.isPending ? 'Signing in...' : 'Sign in'}
            </button>
            <button type="button" className="btn small" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}
