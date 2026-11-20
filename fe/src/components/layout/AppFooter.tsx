import { Link } from 'react-router-dom'

export default function AppFooter() {
  return (
    <footer>
      <div>
        <Link className="brand" to="/">
          UdyamCred
        </Link>
        <p>
          Credit for shops that sell every day but have no credit score. Built for The Big Hack
          2.0, Finance Track.
        </p>
      </div>
      <p className="small">
        All shops, bills and repayments shown here are synthetic. GSTIN format checks are real.
        Registry, bank, UPI and supplier confirmations are mocked. A real deployment needs a full
        compliance review. This tool supports a loan officer and does not replace one.
      </p>
    </footer>
  )
}
