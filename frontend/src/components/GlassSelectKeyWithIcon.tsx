import { useRef, useEffect, type ReactNode } from 'react'
import { GlassButton } from './GlassButton'
import './GlassSelectKeyWithIcon.css'

export interface GlassSelectOption {
  value: string | number
  label: string
  icon?: ReactNode
}

interface GlassSelectKeyWithIconProps {
  options: GlassSelectOption[]
  value: string | number
  onChange: (value: string | number) => void
  placeholder?: string
  icon?: ReactNode
  className?: string
}

/**
 * Универсальный компонент стеклянной кнопки с select внутри
 * По аналогии с GlassMenuButton и GlassObjectsButton
 * Можно использовать с иконкой или без
 */
export default function GlassSelectKeyWithIcon({
  options,
  value,
  onChange,
  placeholder = 'Выберите...',
  icon,
  className = '',
}: GlassSelectKeyWithIconProps): JSX.Element {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const selectRef = useRef<HTMLSelectElement>(null)

  const selectedOption = options.find((opt) => String(opt.value) === String(value))
  const displayText = selectedOption?.label || placeholder

  useEffect(() => {
    const wrapper = wrapperRef.current
    const select = selectRef.current
    if (!wrapper || !select) return

    // Определяем, touch-устройство или нет
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0

    const openSelect = (): void => {
      // Программно открываем select
      if (select) {
        select.focus()
        // Для мобильных устройств используем click
        if (isTouchDevice) {
          select.click()
        } else {
          // Для десктопа создаем событие mousedown
          const event = new MouseEvent('mousedown', { bubbles: true, cancelable: true })
          select.dispatchEvent(event)
        }
      }
    }

    const handleTouchStart = (e: TouchEvent): void => {
      const target = e.target as Node
      if (target !== select && wrapper.contains(target) && !select.contains(target)) {
        e.preventDefault()
        e.stopPropagation()
        openSelect()
      }
    }

    const handleClick = (e: MouseEvent): void => {
      // На touch-устройствах полностью игнорируем click события
      if (isTouchDevice) {
        e.preventDefault()
        e.stopPropagation()
        return
      }

      // Для не-touch устройств обрабатываем click
      const target = e.target as Node
      if (target !== select && wrapper.contains(target) && !select.contains(target)) {
        e.preventDefault()
        e.stopPropagation()
        openSelect()
      }
    }

    if (isTouchDevice) {
      wrapper.addEventListener('touchstart', handleTouchStart, { passive: false })
      wrapper.addEventListener('click', handleClick, { passive: false, capture: true })
    } else {
      wrapper.addEventListener('click', handleClick, { passive: false })
    }

    return () => {
      if (isTouchDevice) {
        wrapper.removeEventListener('touchstart', handleTouchStart)
        wrapper.removeEventListener('click', handleClick, { capture: true })
      } else {
        wrapper.removeEventListener('click', handleClick)
      }
    }
  }, [])

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const selectedValue = e.target.value
    const option = options.find((opt) => String(opt.value) === selectedValue)
    if (option) {
      onChange(option.value)
    }
  }

  return (
    <div ref={wrapperRef} className={`glass-select-key-with-icon-wrapper ${className}`}>
      <GlassButton className="glass-select-key-button">
        {icon && <span className="glass-select-key-icon">{icon}</span>}
      </GlassButton>
      <select
        ref={selectRef}
        className="glass-select-key-native"
        value={String(value)}
        onChange={handleSelectChange}
      >
        {!selectedOption && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={String(opt.value)} value={String(opt.value)}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

