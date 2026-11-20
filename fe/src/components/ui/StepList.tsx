interface Step {
  title: string
  desc: string
}

interface Props {
  steps: Step[]
}

export default function StepList({ steps }: Props) {
  return (
    <ol className="sheet steps">
      {steps.map((s, i) => (
        <li key={i}>
          <div>
            <b>{s.title}</b>
            <span>{s.desc}</span>
          </div>
        </li>
      ))}
    </ol>
  )
}
