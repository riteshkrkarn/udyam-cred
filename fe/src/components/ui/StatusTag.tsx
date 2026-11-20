interface Props {
  status: 'live' | 'soon'
}

const labels = { live: 'Working now', soon: 'Coming soon' }

export default function StatusTag({ status }: Props) {
  return <em className={`tag ${status}`}>{labels[status]}</em>
}
