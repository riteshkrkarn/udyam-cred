import { type ReactNode } from 'react'
import AppHeader from './AppHeader'
import AppFooter from './AppFooter'

interface Props {
  children: ReactNode
}

export default function PublicLayout({ children }: Props) {
  return (
    <div className="page">
      <AppHeader />
      <main>{children}</main>
      <AppFooter />
    </div>
  )
}
