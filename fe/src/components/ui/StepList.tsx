interface Step {
  num: number
  title: string
  desc: string
}

interface Props {
  steps: Step[]
  current?: number
}

export default function StepList({ steps, current }: Props) {
  return (
    <ol className="sheet steps">
      {steps.map((s) => (
        <li key={s.num} className={current === s.num ? 'active' : ''}>
          <div>
            <b>{s.title}</b>
            <span>{s.desc}</span>
          </div>
        </li>
      ))}
    </ol>
  )
}
