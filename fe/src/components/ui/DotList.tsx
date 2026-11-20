interface Props {
  items: string[]
  tone?: 'default' | 'ok' | 'warn'
}

export default function DotList({ items, tone = 'default' }: Props) {
  const cls = tone === 'ok' ? 'dots ok' : tone === 'warn' ? 'dots warn' : 'dots'
  return (
    <ul className={cls}>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  )
}
