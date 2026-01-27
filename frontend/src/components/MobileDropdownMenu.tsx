import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import './MobileDropdownMenu.css'

interface MobileDropdownMenuProps {
  objects?: Array<{ object_id: string | number; [key: string]: unknown }>
  onObjectSelect?: (objectId: string | number) => void
}

export default function MobileDropdownMenu({ objects, onObjectSelect }: MobileDropdownMenuProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(false)
  const [isObjectsMenuOpen, setIsObjectsMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { theme } = useTheme()

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent): void => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setIsObjectsMenuOpen(false)
      }
    }

    if (isOpen || isObjectsMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, isObjectsMenuOpen])

  const handleMenuToggle = (): void => {
    setIsOpen(!isOpen)
    setIsObjectsMenuOpen(false)
  }

  const handleObjectsMenuToggle = (): void => {
    setIsObjectsMenuOpen(!isObjectsMenuOpen)
    setIsOpen(false)
  }

  const handleObjectClick = (objectId: string | number): void => {
    if (onObjectSelect) {
      onObjectSelect(objectId)
    } else {
      navigate(`/user/dashboard/objects/${objectId}`)
    }
    setIsObjectsMenuOpen(false)
  }

  return (
    <div className="mobile-dropdown-menu" ref={menuRef}>
      <button
        className="mobile-menu-button"
        onClick={handleMenuToggle}
        aria-label="Меню быстрых действий"
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
            <span>Создать</span>
          </Link>
          <div className="mobile-dropdown-item" onClick={handleObjectsMenuToggle}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>Объекты</span>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 12L10 8L6 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>
      )}

      {isObjectsMenuOpen && objects && objects.length > 0 && (
        <div className="mobile-dropdown-content mobile-dropdown-nested">
          {objects.map((obj) => (
            <button
              key={obj.object_id}
              className="mobile-dropdown-item"
              onClick={() => handleObjectClick(obj.object_id)}
            >
              <span>{obj.object_id}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

