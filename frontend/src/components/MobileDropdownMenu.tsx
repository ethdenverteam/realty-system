import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import BottomNavDropdown, { createNavigationOptions, createObjectOptions } from './BottomNavDropdown'
import type { RealtyObjectListItem } from '../types/models'
import './MobileDropdownMenu.css'

interface MobileDropdownMenuProps {
  objects?: RealtyObjectListItem[]
  onObjectSelect?: (objectId: string | number) => void
  type?: 'objects' | 'menu'
}

export default function MobileDropdownMenu({ objects, onObjectSelect, type = 'menu' }: MobileDropdownMenuProps): JSX.Element {
  const navigate = useNavigate()
  const { theme } = useTheme()

  // Преобразование объектов из БД в опции для Dropdown
  const objectOptions = createObjectOptions(objects || [])

  const handleNavigationSelect = (value: string | number): void => {
    // Немедленная навигация при выборе (как в onChange для select)
    const path = String(value)
    navigate(path)
    // Прокручиваем к началу страницы
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleObjectSelect = (value: string | number): void => {
    // Немедленное открытие объекта при выборе (как в onChange для select)
    if (onObjectSelect) {
      onObjectSelect(value)
    } else {
      const path = `/user/dashboard/objects/${value}`
      navigate(path)
      // Прокручиваем к началу страницы
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  if (type === 'objects') {
    return (
      <BottomNavDropdown
        options={objectOptions}
        onSelect={handleObjectSelect}
        triggerIcon={
          <img 
            src="/SVG/objects_down.svg" 
            alt="Объекты" 
            width="24" 
            height="24" 
            style={{ filter: theme === 'dark' ? 'invert(1)' : 'none' }} 
          />
        }
        triggerLabel="Быстрый доступ к объектам"
        emptyText="Нет объектов"
      />
    )
  }

  return (
    <BottomNavDropdown
      options={createNavigationOptions()}
      onSelect={handleNavigationSelect}
      triggerIcon={
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M3 12H21M3 6H21M3 18H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      }
      triggerLabel="Меню навигации"
    />
  )
}

