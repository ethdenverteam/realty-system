import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import QuickAccessObjects from './QuickAccessObjects'
import './MobileDropdownMenu.css'

interface MobileDropdownMenuProps {
  objects?: Array<{ object_id: string | number; [key: string]: unknown }>
  onObjectSelect?: (objectId: string | number) => void
  type?: 'objects' | 'menu'
}

export default function MobileDropdownMenu({ objects, onObjectSelect, type = 'menu' }: MobileDropdownMenuProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { theme } = useTheme()

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

  const handleMenuToggle = (): void => {
    setIsOpen(!isOpen)
  }

  if (type === 'objects') {
    return (
      <div className="mobile-dropdown-menu mobile-dropdown-objects" ref={menuRef}>
        <button
          className="mobile-menu-button"
          onClick={handleMenuToggle}
          aria-label="Быстрый доступ к объектам"
        >
          <img src="/SVG/objects_down.svg" alt="Объекты" width="24" height="24" style={{ filter: theme === 'dark' ? 'invert(1)' : 'none' }} />
        </button>
        {isOpen && (
          <QuickAccessObjects objects={objects} onClose={() => setIsOpen(false)} />
        )}
      </div>
    )
  }

  return (
    <div className="mobile-dropdown-menu" ref={menuRef}>
      <button
        className="mobile-menu-button"
        onClick={handleMenuToggle}
        aria-label="Меню навигации"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M3 12H21M3 6H21M3 18H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>

      {isOpen && (
        <div className="mobile-dropdown-content">
          <Link
            to="/user/dashboard"
            className="mobile-dropdown-item"
            onClick={() => setIsOpen(false)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z"
                fill="currentColor"
              />
            </svg>
            <span>Главная</span>
          </Link>
          <Link
            to="/user/dashboard/objects/create"
            className="mobile-dropdown-item"
            onClick={() => setIsOpen(false)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M10 4V16M4 10H16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
            <span>Создать объект</span>
          </Link>
          <Link
            to="/user/dashboard/objects"
            className="mobile-dropdown-item"
            onClick={() => setIsOpen(false)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>Мои объекты</span>
          </Link>
          <Link
            to="/user/dashboard/autopublish"
            className="mobile-dropdown-item"
            onClick={() => setIsOpen(false)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M10 2L2 7L10 12L18 7L10 2Z"
                fill="currentColor"
              />
            </svg>
            <span>Автопубликация</span>
          </Link>
          <Link
            to="/user/dashboard/chats"
            className="mobile-dropdown-item"
            onClick={() => setIsOpen(false)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>Чаты</span>
          </Link>
          <Link
            to="/user/dashboard/telegram-accounts"
            className="mobile-dropdown-item"
            onClick={() => setIsOpen(false)}
          >
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
            <span>Тг аккаунт</span>
          </Link>
          <Link
            to="/user/dashboard/settings"
            className="mobile-dropdown-item"
            onClick={() => setIsOpen(false)}
          >
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
            <span>Настройки</span>
          </Link>
        </div>
      )}
    </div>
  )
}

