import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { DropdownOption } from './Dropdown'
import type { RealtyObjectListItem } from '../types/models'
import './BottomNavDropdown.css'

interface BottomNavDropdownProps {
  options: DropdownOption[]
  onSelect: (value: string | number) => void
  triggerIcon: React.ReactNode
  triggerLabel: string
  emptyText?: string
  className?: string
}

/**
 * Универсальный компонент выпадающего меню для нижней панели навигации
 * Работает по аналогии с выбором района на странице "Мои объекты"
 */
export default function BottomNavDropdown({
  options,
  onSelect,
  triggerIcon,
  triggerLabel,
  emptyText = 'Нет элементов',
  className = '',
}: BottomNavDropdownProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent): void => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
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

  const handleSelect = (value: string | number): void => {
    onSelect(value)
    setIsOpen(false)
  }

  const handleToggle = (): void => {
    setIsOpen(!isOpen)
  }

  return (
    <div className={`bottom-nav-dropdown ${className}`} ref={menuRef}>
      <button
        className="bottom-nav-dropdown-trigger"
        onClick={handleToggle}
        aria-label={triggerLabel}
        aria-expanded={isOpen}
      >
        {triggerIcon}
      </button>
      {isOpen && (
        <div className="bottom-nav-dropdown-menu">
          {options.length === 0 ? (
            <div className="bottom-nav-dropdown-empty">
              <p>{emptyText}</p>
            </div>
          ) : (
            <div className="bottom-nav-dropdown-list">
              {options.map((option) => (
                <button
                  key={String(option.value)}
                  type="button"
                  className={`bottom-nav-dropdown-item ${option.disabled ? 'disabled' : ''}`}
                  onClick={() => !option.disabled && handleSelect(option.value)}
                  disabled={option.disabled}
                >
                  {option.icon && <span className="bottom-nav-dropdown-item-icon">{option.icon}</span>}
                  <span className="bottom-nav-dropdown-item-text">{option.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Хелпер для создания опций навигации
 */
export function createNavigationOptions(): DropdownOption[] {
  return [
    {
      label: 'Главная',
      value: '/user/dashboard',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z" fill="currentColor" />
        </svg>
      ),
    },
    {
      label: 'Создать объект',
      value: '/user/dashboard/objects/create',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M10 4V16M4 10H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      label: 'Мои объекты',
      value: '/user/dashboard/objects',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
    },
    {
      label: 'Автопубликация',
      value: '/user/dashboard/autopublish',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M10 2L2 7L10 12L18 7L10 2Z" fill="currentColor" />
        </svg>
      ),
    },
    {
      label: 'Чаты',
      value: '/user/dashboard/chats',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
    },
    {
      label: 'Тг аккаунт',
      value: '/user/dashboard/telegram-accounts',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M10 10C12.7614 10 15 7.76142 15 5C15 2.23858 12.7614 0 10 0C7.23858 0 5 2.23858 5 5C5 7.76142 7.23858 10 10 10Z"
            fill="currentColor"
          />
          <path
            d="M10 12C5.58172 12 2 14.2386 2 17V20H18V17C18 14.2386 14.4183 12 10 12Z"
            fill="currentColor"
          />
        </svg>
      ),
    },
    {
      label: 'Настройки',
      value: '/user/dashboard/settings',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M10 12C11.1046 12 12 11.1046 12 10C12 8.89543 11.1046 8 10 8C8.89543 8 8 8.89543 8 10C8 11.1046 8.89543 12 10 12Z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M17.6569 10.6569C17.6569 10.6569 17.6569 10.6569 17.6569 10.6569C17.6569 10.6569 17.6569 10.6569 17.6569 10.6569C17.6569 10.6569 17.6569 10.6569 17.6569 10.6569C17.6569 10.6569 17.6569 10.6569 17.6569 10.6569"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
    },
  ]
}

/**
 * Хелпер для преобразования объектов из БД в опции для Dropdown
 */
export function createObjectOptions(objects: RealtyObjectListItem[]): DropdownOption[] {
  return objects.map((obj) => ({
    label: obj.rooms_type && obj.price
      ? `${obj.rooms_type} - ${obj.price} тыс. руб.`
      : `Объект #${obj.object_id}`,
    value: obj.object_id,
    disabled: obj.status === 'архив',
  }))
}

