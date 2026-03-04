import { Link } from 'react-router-dom'
import { useTheme } from '../../contexts/ThemeContext'

interface LayoutHeaderProps {
  title: string
  isAdmin: boolean
  headerActions?: React.ReactNode
}

export function LayoutHeader({ title, isAdmin, headerActions }: LayoutHeaderProps): JSX.Element {
  const { theme, toggleTheme } = useTheme()

  const handleTitleClick = (): void => {
    window.location.reload()
  }

  return (
    <header className={`app-header ${isAdmin ? 'admin' : ''}`}>
      <div className="header-content">
        <h1 className="header-title mobile-title-clickable" onClick={handleTitleClick}>
          {title}
        </h1>
        {!isAdmin && <UserHeaderActions theme={theme} toggleTheme={toggleTheme} />}
        {isAdmin && <AdminHeaderActions theme={theme} toggleTheme={toggleTheme} headerActions={headerActions} />}
      </div>
    </header>
  )
}

function UserHeaderActions({ theme, toggleTheme }: { theme: string; toggleTheme: () => void }): JSX.Element {
  return (
    <div className="header-actions mobile-header-actions">
      <Link
        to="/user/dashboard/objects"
        className="header-icon-btn"
        aria-label="Объекты"
      >
        <img src="/SVG/objects_up.svg" alt="Объекты" width="24" height="24" style={{ filter: 'brightness(0) saturate(100%) invert(27%) sepia(94%) saturate(7151%) hue-rotate(337deg) brightness(101%) contrast(101%)' }} />
      </Link>
      <Link
        to="/user/dashboard/settings"
        className="header-icon-btn"
        aria-label="Настройки"
      >
        <img src="/SVG/settings_up.svg" alt="Настройки" width="24" height="24" style={{ filter: 'brightness(0) saturate(100%) invert(27%) sepia(94%) saturate(7151%) hue-rotate(337deg) brightness(101%) contrast(101%)' }} />
      </Link>
      <ThemeToggleButton theme={theme} toggleTheme={toggleTheme} size={24} />
    </div>
  )
}

function AdminHeaderActions({ theme, toggleTheme, headerActions }: { theme: string; toggleTheme: () => void; headerActions?: React.ReactNode }): JSX.Element {
  return (
    <div className="header-actions">
      {headerActions}
      <ThemeToggleButton theme={theme} toggleTheme={toggleTheme} size={20} />
    </div>
  )
}

function ThemeToggleButton({ theme, toggleTheme, size }: { theme: string; toggleTheme: () => void; size: number }): JSX.Element {
  return (
    <button
      className="header-icon-btn"
      onClick={toggleTheme}
      aria-label={theme === 'dark' ? 'Светлая тема' : 'Темная тема'}
    >
      {theme === 'dark' ? <SunIcon size={size} /> : <MoonIcon size={size} />}
    </button>
  )
}

function SunIcon({ size }: { size: number }): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M12 3V1M12 23V21M21 12H23M1 12H3M18.364 5.636L19.778 4.222M4.222 19.778L5.636 18.364M18.364 18.364L19.778 19.778M4.222 4.222L5.636 5.636M17 12C17 14.7614 14.7614 17 12 17C9.23858 17 7 14.7614 7 12C7 9.23858 9.23858 7 12 7C14.7614 7 17 9.23858 17 12Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function MoonIcon({ size }: { size: number }): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"
        fill="currentColor"
      />
    </svg>
  )
}

