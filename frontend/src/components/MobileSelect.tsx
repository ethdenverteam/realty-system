import { useState, useRef, useEffect } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import './MobileSelect.css'

interface MobileSelectOption {
  value: string
  label: string
}

interface MobileSelectProps {
  value: string
  onChange: (value: string) => void
  options: MobileSelectOption[]
  placeholder?: string
  label?: string
  className?: string
}

export default function MobileSelect({
  value,
  onChange,
  options,
  placeholder = 'Выберите...',
  label,
  className = '',
}: MobileSelectProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(false)
  const selectRef = useRef<HTMLDivElement>(null)
  const { theme } = useTheme()

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

  const selectedOption = options.find((opt) => opt.value === value)
  const displayValue = selectedOption ? selectedOption.label : placeholder

  const handleSelect = (optionValue: string): void => {
    onChange(optionValue)
    setIsOpen(false)
  }

  return (
    <div className={`mobile-select ${className}`} ref={selectRef}>
      {label && <label className="mobile-select-label">{label}</label>}
      <button
        type="button"
        className="mobile-select-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={label || placeholder}
      >
        <span className="mobile-select-value">{displayValue}</span>
        <svg
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          className={`mobile-select-arrow ${isOpen ? 'open' : ''}`}
        >
          <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {isOpen && (
        <div className="mobile-select-dropdown">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`mobile-select-option ${value === option.value ? 'selected' : ''}`}
              onClick={() => handleSelect(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

