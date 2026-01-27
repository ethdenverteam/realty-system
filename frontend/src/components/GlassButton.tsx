import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './Glass.css'

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

export function GlassButton({
  children,
  leftIcon,
  rightIcon,
  className = '',
  ...rest
}: GlassButtonProps): JSX.Element {
  return (
    <button className={`glass-button ${className}`.trim()} type="button" {...rest}>
      {leftIcon && <span>{leftIcon}</span>}
      <span>{children}</span>
      {rightIcon && <span>{rightIcon}</span>}
    </button>
  )
}

import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './Glass.css'

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode
}

/**
 * Стеклянная кнопка в духе Liquid Glass (плавающая, полупрозрачная).
 */
export function GlassButton({ icon, children, className = '', ...rest }: GlassButtonProps): JSX.Element {
  return (
    <button className={`glass-button ${className}`} type="button" {...rest}>
      {icon && <span className="glass-button-icon">{icon}</span>}
      {children && <span className="glass-button-label">{children}</span>}
    </button>
  )
}


