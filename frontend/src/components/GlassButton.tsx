import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './Glass.css'

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode
}

/**
 * Стеклянная кнопка в духе Liquid Glass (плавающая, полупрозрачная).
 */
export function GlassButton({ icon, children, className = '', onClick, ...rest }: GlassButtonProps): JSX.Element {
  // Если это кнопка с select внутри, не добавляем onClick на саму кнопку
  const handleClick = className.includes('glass-select-button') ? undefined : onClick

  return (
    <button className={`glass-button ${className}`} type="button" onClick={handleClick} {...rest}>
      {icon && <span className="glass-button-icon">{icon}</span>}
      {children && <span className="glass-button-label">{children}</span>}
    </button>
  )
}


