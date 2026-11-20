interface Row {
  label: string
  value: string
  highlight?: boolean
  total?: boolean
}

interface Props {
  rows: Row[]
}

export default function LedgerTable({ rows }: Props) {
  return (
    <table className="rows">
      <tbody>
        {rows.map((r, i) => (
          <tr
            key={i}
            className={r.total ? 'total' : r.highlight ? 'hl' : undefined}
          >
            <td>{r.label}</td>
            <td>{r.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
