import { Link, useLocation } from 'react-router-dom'
import GlassObjectsButton from '../GlassObjectsButton'
import GlassMenuButton from '../GlassMenuButton'
import type { RealtyObjectListItem } from '../../types/models'

interface LayoutBottomNavProps {
  isAdmin: boolean
  objects: RealtyObjectListItem[]
}

export function LayoutBottomNav({ isAdmin, objects }: LayoutBottomNavProps): JSX.Element {
  const location = useLocation()

  if (isAdmin) {
    return <AdminBottomNav location={location} />
  }

  return <UserBottomNav location={location} objects={objects} />
}

function AdminBottomNav({ location }: { location: ReturnType<typeof useLocation> }): JSX.Element {
  return (
    <nav className="bottom-nav">
      <Link
        to="/admin/dashboard"
        className={`nav-item ${location.pathname === '/admin/dashboard' ? 'active' : ''}`}
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z" fill="currentColor" />
        </svg>
        <span>Главная</span>
      </Link>
      <Link to="/user/dashboard" className="nav-item">
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
        <span>Пользователь</span>
      </Link>
    </nav>
  )
}

function UserBottomNav({ location, objects }: { location: ReturnType<typeof useLocation>; objects: RealtyObjectListItem[] }): JSX.Element {
  return (
    <nav className="bottom-nav mobile-bottom-nav">
      <Link
        to="/user/dashboard"
        className={`bottom-nav-icon-btn ${location.pathname === '/user/dashboard' ? 'active' : ''}`}
        aria-label="Главная"
      >
        <img src="/SVG/dashboard_down.svg" alt="Главная" width="24" height="24" style={{ filter: 'brightness(0) saturate(100%) invert(27%) sepia(94%) saturate(7151%) hue-rotate(337deg) brightness(101%) contrast(101%)' }} />
      </Link>
      <Link
        to="/user/dashboard/objects/create"
        className={`bottom-nav-icon-btn ${location.pathname.includes('/create') ? 'active' : ''}`}
        aria-label="Создать"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 4V20M4 12H20"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </Link>
      <div className="bottom-nav-glass-menu">
        <GlassObjectsButton objects={objects} />
      </div>
      <div className="bottom-nav-glass-menu">
        <GlassMenuButton />
      </div>
    </nav>
  )
}

