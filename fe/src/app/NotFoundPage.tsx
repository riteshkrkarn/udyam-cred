import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div style={{ padding: '6rem 2rem', maxWidth: 480 }}>
      <p className="eyebrow">404</p>
      <h1 style={{ marginTop: '0.5rem' }}>Page not found</h1>
      <p className="lead" style={{ marginTop: '1rem' }}>
        The page you are looking for does not exist or has moved.
      </p>
      <div className="actions" style={{ marginTop: '2rem' }}>
        <Link className="btn green" to="/">
          Back to home
        </Link>
      </div>
    </div>
  )
}
