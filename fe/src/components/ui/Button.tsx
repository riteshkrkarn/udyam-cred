import { type ButtonHTMLAttributes, type AnchorHTMLAttributes } from 'react'
import { Link, type LinkProps } from 'react-router-dom'

type Variant = 'red' | 'green' | 'haldi' | 'ghost' | 'small'
type Size = 'default' | 'small'

interface BaseProps {
  variant?: Variant
  /** Render as a react-router Link */
  to?: string
  /** Render as a plain anchor */
  href?: string
}

type ButtonProps = BaseProps & ButtonHTMLAttributes<HTMLButtonElement>
type AnchorProps = BaseProps & AnchorHTMLAttributes<HTMLAnchorElement>

type Props = ButtonProps | AnchorProps

function classes(variant: Variant = 'green') {
  return `btn ${variant}`
}

export default function Button({ variant = 'green', to, href, children, ...rest }: Props & { children?: React.ReactNode }) {
  const cls = classes(variant)
  if (to) {
    return (
      <Link className={cls} to={to} {...(rest as Omit<LinkProps, 'to'>)}>
        {children}
      </Link>
    )
  }
  if (href) {
    return (
      <a className={cls} href={href} {...(rest as AnchorHTMLAttributes<HTMLAnchorElement>)}>
        {children}
      </a>
    )
  }
  return (
    <button className={cls} {...(rest as ButtonHTMLAttributes<HTMLButtonElement>)}>
      {children}
    </button>
  )
}
