import { type ReactNode } from 'react'

interface Props {
  children: ReactNode
  as?: keyof JSX.IntrinsicElements
  className?: string
  style?: React.CSSProperties
  ariaLive?: 'polite' | 'assertive' | 'off'
}

export default function Sheet({ children, as: Tag = 'div', className = '', style, ariaLive }: Props) {
  return (
    <Tag className={`sheet ${className}`.trim()} style={style} aria-live={ariaLive}>
      {children}
    </Tag>
  )
}
