import { useRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import './Glass.css'

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode
}

/**
 * Стеклянная кнопка в духе Liquid Glass (плавающая, полупрозрачная).
 * Автоматически добавляет glow эффект при клике.
 */
export function GlassButton({ icon, children, className = '', onClick, ...rest }: GlassButtonProps): JSX.Element {
  const buttonRef = useRef<HTMLButtonElement>(null)

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>): void => {
    // Добавляем glow эффект
    const button = buttonRef.current
    if (button) {
      button.classList.add('glow-active')
      setTimeout(() => {
        button.classList.remove('glow-active')
      }, 400)
    }
    onClick?.(e)
  }

  return (
    <button 
      ref={buttonRef}
      className={`glass-button ${className}`} 
      type="button" 
      onClick={handleClick}
      {...rest}
    >
      {icon && <span className="glass-button-icon">{icon}</span>}
      {children && <span className="glass-button-label">{children}</span>}
    </button>
  )
}


