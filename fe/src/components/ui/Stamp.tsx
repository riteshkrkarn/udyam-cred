import { type Verdict } from '../../engine/reconcile'

const labels: Record<Verdict, string> = {
  match: 'Match',
  review: 'Under Review',
  mismatch: 'Mismatch',
}

interface Props {
  verdict: Verdict
}

export default function Stamp({ verdict }: Props) {
  return <span className={`stamp ${verdict}`}>{labels[verdict]}</span>
}
