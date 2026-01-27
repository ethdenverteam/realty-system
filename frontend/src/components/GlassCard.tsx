import { useRef, type ReactNode, type HTMLAttributes } from 'react'
import './Glass.css'

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  className?: string
}

/**
 * Базовая стеклянная карточка (glassmorphism), которую можно переиспользовать по всему приложению.
 * Автоматически добавляет glow эффект при клике, если есть onClick обработчик.
 */
export function GlassCard({ children, className = '', onClick, ...rest }: GlassCardProps): JSX.Element {
  const cardRef = useRef<HTMLDivElement>(null)

  const handleClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    // Добавляем glow эффект только если есть onClick
    if (onClick) {
      const card = cardRef.current
      if (card) {
        card.classList.add('glow-active')
        setTimeout(() => {
          card.classList.remove('glow-active')
        }, 400)
      }
    }
    onClick?.(e)
  }

  return (
    <div 
      ref={cardRef}
      className={`glass-card ${className}`}
      onClick={handleClick}
      {...rest}
    >
      {children}
    </div>
  )
}


