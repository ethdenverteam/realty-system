import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import Dropdown, { type DropdownOption } from './Dropdown'
import type { RealtyObjectListItem } from '../types/models'
import './MobileDropdownMenu.css'

interface MobileDropdownMenuProps {
  objects?: RealtyObjectListItem[]
  onObjectSelect?: (objectId: string | number) => void
  type?: 'objects' | 'menu'
}

// Данные для навигационного меню
const NAVIGATION_OPTIONS: DropdownOption[] = [
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

export default function MobileDropdownMenu({ objects, onObjectSelect, type = 'menu' }: MobileDropdownMenuProps): JSX.Element {
  const navigate = useNavigate()
  const { theme } = useTheme()
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

  // Преобразование объектов из БД в формат для Dropdown
  const objectOptions: DropdownOption[] = (objects || []).map((obj) => ({
    label: obj.rooms_type && obj.price
      ? `${obj.rooms_type} - ${obj.price} тыс. руб.`
      : `Объект #${obj.object_id}`,
    value: obj.object_id,
  }))

  const handleNavigationChange = (value: string | number): void => {
    navigate(String(value))
    setIsOpen(false)
  }

  const handleObjectChange = (value: string | number): void => {
    if (onObjectSelect) {
      onObjectSelect(value)
    } else {
      navigate(`/user/dashboard/objects/${value}`)
    }
    setIsOpen(false)
  }

  const handleToggle = (): void => {
    setIsOpen(!isOpen)
  }

  if (type === 'objects') {
    return (
      <div className="mobile-dropdown-menu mobile-dropdown-objects" ref={menuRef}>
        <button
          className="mobile-menu-button"
          onClick={handleToggle}
          aria-label="Быстрый доступ к объектам"
        >
          <img 
            src="/SVG/objects_down.svg" 
            alt="Объекты" 
            width="24" 
            height="24" 
            style={{ filter: theme === 'dark' ? 'invert(1)' : 'none' }} 
          />
        </button>
        {isOpen && (
          <div className="mobile-dropdown-wrapper">
            <Dropdown
              options={objectOptions}
              defaultText="Выберите объект"
              onChange={handleObjectChange}
              variant="mobile"
              position="top"
              className="mobile-dropdown-custom"
              placeholder={objectOptions.length === 0 ? 'Нет объектов' : 'Выберите объект'}
              defaultOpen={true}
              hideButton={true}
            />
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="mobile-dropdown-menu" ref={menuRef}>
      <button
        className="mobile-menu-button"
        onClick={handleToggle}
        aria-label="Меню навигации"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M3 12H21M3 6H21M3 18H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>
      {isOpen && (
        <div className="mobile-dropdown-wrapper">
          <Dropdown
            options={NAVIGATION_OPTIONS}
            defaultText="Меню"
            onChange={handleNavigationChange}
            variant="mobile"
            position="top"
            className="mobile-dropdown-custom"
            placeholder="Меню навигации"
            defaultOpen={true}
            hideButton={true}
          />
        </div>
      )}
    </div>
  )
}

