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
    // Немедленно применяем действие при выборе
    onSelect(value)
    // Закрываем меню после выбора
    setIsOpen(false)
  }

  const triggerRef = useRef<HTMLButtonElement>(null)

  const handleToggle = (): void => {
    // Добавляем glow эффект при клике
    const trigger = triggerRef.current
    if (trigger) {
      trigger.classList.add('glow-active')
      setTimeout(() => {
        trigger.classList.remove('glow-active')
      }, 400)
    }
    setIsOpen(!isOpen)
  }

  return (
    <div className={`bottom-nav-dropdown ${className}`} ref={menuRef}>
      <button
        ref={triggerRef}
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
export function createNavigationOptions(isAdmin: boolean = false): DropdownOption[] {
  const options: DropdownOption[] = [
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
      label: 'Telegram аккаунты',
      value: '/user/dashboard/telegram-accounts',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M10 2C8.89543 2 8 2.89543 8 4C8 5.10457 8.89543 6 10 6C11.1046 6 12 5.10457 12 4C12 2.89543 11.1046 2 10 2Z"
            fill="currentColor"
          />
          <path
            d="M5 16C5 13.7909 7.23858 12 10 12C12.7614 12 15 13.7909 15 16V18H5V16Z"
            fill="currentColor"
          />
          <path
            d="M16 8C16 9.10457 16.8954 10 18 10C19.1046 10 20 9.10457 20 8C20 6.89543 19.1046 6 18 6C16.8954 6 16 6.89543 16 8Z"
            fill="currentColor"
          />
          <path
            d="M13 14C13 12.3431 15.2386 11 18 11C20.7614 11 23 12.3431 23 14V16H13V14Z"
            fill="currentColor"
          />
        </svg>
      ),
    },
    {
      label: 'Подписка на чаты',
      value: '/user/dashboard/chat-subscriptions',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="2" cy="5" r="1.5" fill="currentColor" />
          <circle cx="2" cy="10" r="1.5" fill="currentColor" />
          <circle cx="2" cy="15" r="1.5" fill="currentColor" />
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
  
  // Добавляем пункт для админов в самый низ
  if (isAdmin) {
    options.push({
      label: 'Админ панель',
      value: '/admin/dashboard',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M10 2L2 7L10 12L18 7L10 2Z"
            fill="currentColor"
          />
          <path
            d="M2 13L10 18L18 13M2 10L10 15L18 10"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
    })
  }
  
  return options
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

