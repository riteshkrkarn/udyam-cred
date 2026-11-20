import { useState } from 'react'

interface Props {
  title: string
  items: string[]
  expanded?: boolean
}

/**
 * Displays a collapsible box with reasoning items (bullet points).
 * Each item can contain markdown-style **bold** and links.
 */
export default function ReasoningBox({ title, items, expanded = false }: Props) {
  const [isOpen, setIsOpen] = useState(expanded)

  // Simple markdown: convert **text** to <strong>
  function renderText(text: string) {
    return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>
      }
      return part
    })
  }

  return (
    <div style={{ marginBottom: '1.5rem', borderLeft: '3px solid var(--haldi)', paddingLeft: '1rem' }}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          font: 'inherit',
          color: 'var(--ink)',
          fontWeight: 600,
          fontSize: 14,
          padding: 0,
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: '1.2em',
            textAlign: 'center',
            transition: 'transform 200ms',
            transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
          }}
        >
          ▶
        </span>
        {title}
      </button>

      {isOpen && (
        <ul
          style={{
            marginTop: '0.75rem',
            marginBottom: 0,
            paddingLeft: '1.5rem',
            listStyle: 'disc',
            color: 'var(--sec)',
            fontSize: 14,
            lineHeight: 1.6,
          }}
        >
          {items.map((item, i) => (
            <li key={i} style={{ marginBottom: '0.5rem' }}>
              {renderText(item)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
