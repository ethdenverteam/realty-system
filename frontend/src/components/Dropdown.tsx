import { useState, useRef, useEffect } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import './Dropdown.css'

// Интерфейс для пункта меню
export interface DropdownOption {
  label: string
  value: string | number
  disabled?: boolean
  selected?: boolean
  icon?: React.ReactNode
  group?: string
}

// Пропсы для компонента Dropdown
export interface DropdownProps {
  options: DropdownOption[]
  defaultText?: string
  onChange: (value: string | number) => void
  className?: string
  required?: boolean
  value?: string | number
  placeholder?: string
  label?: string
  variant?: 'default' | 'mobile' | 'form'
  position?: 'bottom' | 'top' | 'auto'
  maxHeight?: string
  defaultOpen?: boolean
  onOpenChange?: (isOpen: boolean) => void
  hideButton?: boolean
}

export default function Dropdown({
  options,
  defaultText = 'Выберите...',
  onChange,
  className = '',
  required = false,
  value,
  placeholder,
  variant = 'default',
  position = 'auto',
  maxHeight = '300px',
  label,
  defaultOpen = false,
  onOpenChange,
  hideButton = false,
}: DropdownProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  const selectRef = useRef<HTMLDivElement>(null)
  const { theme } = useTheme()

  useEffect(() => {
    if (defaultOpen !== undefined) {
      setIsOpen(defaultOpen)
    }
  }, [defaultOpen])

  useEffect(() => {
    if (onOpenChange) {
      onOpenChange(isOpen)
    }
  }, [isOpen, onOpenChange])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent): void => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const selectedOption = value !== undefined 
    ? options.find((opt) => opt.value === value)
    : options.find((opt) => opt.selected)

  const displayValue = selectedOption ? selectedOption.label : (placeholder || defaultText)

  const handleSelect = (optionValue: string | number): void => {
    onChange(optionValue)
    setIsOpen(false)
  }

  // Группировка опций по группам (если есть)
  const groupedOptions = options.reduce((acc, option) => {
    const group = option.group || 'default'
    if (!acc[group]) {
      acc[group] = []
    }
    acc[group].push(option)
    return acc
  }, {} as Record<string, DropdownOption[]>)

  const hasGroups = Object.keys(groupedOptions).length > 1 || (Object.keys(groupedOptions).length === 1 && Object.keys(groupedOptions)[0] !== 'default')

  // Определяем позицию dropdown
  const getDropdownPosition = (): string => {
    if (position !== 'auto') return position
    // Автоматическое определение позиции на основе доступного пространства
    if (selectRef.current) {
      const rect = selectRef.current.getBoundingClientRect()
      const spaceBelow = window.innerHeight - rect.bottom
      const spaceAbove = rect.top
      return spaceBelow < 200 && spaceAbove > spaceBelow ? 'top' : 'bottom'
    }
    return 'bottom'
  }

  const dropdownPosition = getDropdownPosition()

  return (
    <div 
      className={`dropdown dropdown-${variant} ${className}`} 
      ref={selectRef}
      data-required={required}
    >
      {label && <label className="dropdown-label">{label}</label>}
      {!hideButton && (
        <button
          type="button"
          className={`dropdown-button ${isOpen ? 'open' : ''} ${!selectedOption && required ? 'required' : ''}`}
          onClick={() => setIsOpen(!isOpen)}
          aria-label={label || placeholder || defaultText}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        >
          <span className="dropdown-value">
            {selectedOption?.icon && <span className="dropdown-icon">{selectedOption.icon}</span>}
            <span className="dropdown-text">{displayValue}</span>
          </span>
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            className={`dropdown-arrow ${isOpen ? 'open' : ''}`}
          >
            <path 
              d="M5 7.5L10 12.5L15 7.5" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
            />
          </svg>
        </button>
      )}
      {(isOpen || hideButton) && (
        <div 
          className={`dropdown-menu dropdown-menu-${dropdownPosition} ${hideButton ? 'dropdown-menu-no-button' : ''}`}
          style={{ maxHeight }}
          role="listbox"
        >
          {hasGroups ? (
            Object.entries(groupedOptions).map(([groupName, groupOptions]) => (
              <div key={groupName} className="dropdown-group">
                {groupName !== 'default' && (
                  <div className="dropdown-group-label">{groupName}</div>
                )}
                {groupOptions.map((option) => (
                  <button
                    key={String(option.value)}
                    type="button"
                    className={`dropdown-option ${value === option.value ? 'selected' : ''} ${option.disabled ? 'disabled' : ''}`}
                    onClick={() => !option.disabled && handleSelect(option.value)}
                    disabled={option.disabled}
                    role="option"
                    aria-selected={value === option.value}
                  >
                    {option.icon && <span className="dropdown-option-icon">{option.icon}</span>}
                    <span className="dropdown-option-text">{option.label}</span>
                  </button>
                ))}
              </div>
            ))
          ) : (
            options.map((option) => (
              <button
                key={String(option.value)}
                type="button"
                className={`dropdown-option ${value === option.value ? 'selected' : ''} ${option.disabled ? 'disabled' : ''}`}
                onClick={() => !option.disabled && handleSelect(option.value)}
                disabled={option.disabled}
                role="option"
                aria-selected={value === option.value}
              >
                {option.icon && <span className="dropdown-option-icon">{option.icon}</span>}
                <span className="dropdown-option-text">{option.label}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

