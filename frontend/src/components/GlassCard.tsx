import type { ReactNode } from 'react'
import './Glass.css'

interface GlassCardProps {
  children: ReactNode
  className?: string
}

export function GlassCard({ children, className = '' }: GlassCardProps): JSX.Element {
  return <div className={`glass-card ${className}`.trim()}>{children}</div>
}

import type { ReactNode } from 'react'
import './Glass.css'

interface GlassCardProps {
  children: ReactNode
  className?: string
}

/**
 * Базовая стеклянная карточка (glassmorphism), которую можно переиспользовать по всему приложению.
 */
export function GlassCard({ children, className = '' }: GlassCardProps): JSX.Element {
  return <div className={`glass-card ${className}`}>{children}</div>
}


