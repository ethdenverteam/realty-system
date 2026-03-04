import type { ReactNode } from 'react'
import { LayoutHeader } from './layout/LayoutHeader'
import { LayoutTopNav } from './layout/LayoutTopNav'
import { LayoutBottomNav } from './layout/LayoutBottomNav'
import { useObjects } from '../hooks/useObjects'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
  title: string
  headerActions?: ReactNode
  isAdmin?: boolean
}

export default function Layout({
  children,
  title,
  headerActions,
  isAdmin = false,
}: LayoutProps): JSX.Element {
  const objects = useObjects()

  return (
    <div className="app-layout">
      <LayoutHeader title={title} isAdmin={isAdmin} headerActions={headerActions} />
      <LayoutTopNav isAdmin={isAdmin} />
      <main className="app-main">{children}</main>
      <LayoutBottomNav isAdmin={isAdmin} objects={objects} />
    </div>
  )
}


