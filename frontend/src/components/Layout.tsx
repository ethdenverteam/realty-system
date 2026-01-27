import { Link, useLocation, useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import MobileDropdownMenu from './MobileDropdownMenu'
import { useEffect, useState } from 'react'
import api from '../utils/api'
import type { RealtyObjectListItem, ObjectsListResponse } from '../types/models'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
  title: string
  headerActions?: ReactNode
  isAdmin?: boolean
}

export default function Layout({
  children,
  title,
  headerActions,
  isAdmin = false,
}: LayoutProps): JSX.Element {
  const { user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const navigate = useNavigate()
  const [objects, setObjects] = useState<RealtyObjectListItem[]>([])

  useEffect(() => {
    if (!isAdmin) {
      void loadObjects()
    }
  }, [isAdmin])

  const loadObjects = async (): Promise<void> => {
    try {
      const res = await api.get<ObjectsListResponse>('/user/dashboard/objects/list', {
        params: { per_page: 100 },
      })
      setObjects(res.data.objects || [])
    } catch (err) {
      console.error('Error loading objects:', err)
    }
  }

  const handleTitleClick = (): void => {
    window.location.reload()
  }

  return (
    <div className="app-layout">
      <header className={`app-header ${isAdmin ? 'admin' : ''}`}>
        <div className="header-content">
          <h1 className="header-title mobile-title-clickable" onClick={handleTitleClick}>
            {title}
          </h1>
          {!isAdmin && (
            <div className="header-actions mobile-header-actions">
              <Link
                to="/user/dashboard/objects"
                className="header-icon-btn"
                aria-label="Объекты"
              >
                <img src="/SVG/objects_up.svg" alt="Объекты" width="24" height="24" style={{ filter: theme === 'dark' ? 'invert(1)' : 'none' }} />
              </Link>
              <Link
                to="/user/dashboard/settings"
                className="header-icon-btn"
                aria-label="Настройки"
              >
                <img src="/SVG/settings_up.svg" alt="Настройки" width="24" height="24" style={{ filter: theme === 'dark' ? 'invert(1)' : 'none' }} />
              </Link>
              <button
                className="header-icon-btn"
                onClick={toggleTheme}
                aria-label={theme === 'dark' ? 'Светлая тема' : 'Темная тема'}
              >
                {theme === 'dark' ? (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 3V1M12 23V21M21 12H23M1 12H3M18.364 5.636L19.778 4.222M4.222 19.778L5.636 18.364M18.364 18.364L19.778 19.778M4.222 4.222L5.636 5.636M17 12C17 14.7614 14.7614 17 12 17C9.23858 17 7 14.7614 7 12C7 9.23858 9.23858 7 12 7C14.7614 7 17 9.23858 17 12Z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"
                      fill="currentColor"
                    />
                  </svg>
                )}
              </button>
            </div>
          )}
          {isAdmin && (
            <div className="header-actions">
              {headerActions}
              <button
                className="header-icon-btn"
                onClick={toggleTheme}
                aria-label={theme === 'dark' ? 'Светлая тема' : 'Темная тема'}
              >
                {theme === 'dark' ? (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path
                      d="M10 3V1M10 19V17M17 10H19M1 10H3M15.657 4.343L16.778 3.222M3.222 16.778L4.343 15.657M15.657 15.657L16.778 16.778M3.222 3.222L4.343 4.343M14 10C14 12.2091 12.2091 14 10 14C7.79086 14 6 12.2091 6 10C6 7.79086 7.79086 6 10 6C12.2091 6 14 7.79086 14 10Z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path
                      d="M17.293 13.293C16.2885 14.2981 15.0335 15.0027 13.6735 15.3169C12.3135 15.6311 10.9018 15.5432 9.58591 15.062C8.27003 14.5808 7.09576 13.7222 6.19218 12.5786C5.28859 11.435 4.6904 10.0475 4.45189 8.57389C4.21338 7.10029 4.34331 5.59314 4.82751 4.18996C5.31172 2.78678 6.13316 1.52786 7.21405 0.516985C8.29495 -0.49389 9.59537 -1.22007 11.0012 -1.59987C12.407 -1.97967 13.8713 -2.00121 15.2872 -1.66241C16.7031 -1.32361 18.0258 -0.633259 19.1407 0.351709C19.2608 0.467003 19.3702 0.592995 19.4673 0.728042C19.4673 0.728042 19.475 0.737209 19.4776 0.74038L19.4879 0.753851L19.502 0.776557L19.5051 0.781138L19.514 0.795373C19.514 0.795373 20.3827 2.34025 19.1407 3.58231C18.6335 4.08946 17.9922 4.46034 17.293 4.66029C16.7118 4.82355 16.1081 4.84887 15.5171 4.73442C14.9261 4.61996 14.3615 4.36839 13.8617 3.99557C13.3619 3.62275 12.9386 3.13718 12.6191 2.57158L12.5848 2.51083C12.5613 2.47142 12.5361 2.43291 12.5092 2.39542C11.7619 3.50919 11.3808 4.78519 11.3808 6.08231C11.3808 9.68885 14.3112 12.6193 17.9177 12.6193C18.8042 12.6193 19.6586 12.4531 20.4476 12.1407C20.4839 12.1271 20.5197 12.1125 20.5549 12.0969C20.5549 12.0969 20.5612 12.0943 20.5644 12.0931L20.5779 12.0876L20.6006 12.0782L20.6052 12.0764L20.6194 12.0706C20.6194 12.0706 19.1407 13.293 17.293 13.293Z"
                      fill="currentColor"
                    />
                  </svg>
                )}
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Top navigation for desktop */}
      <nav className="top-nav">
        {isAdmin ? (
          <>
            <Link
              to="/admin/dashboard"
              className={`top-nav-item ${location.pathname === '/admin/dashboard' ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z" fill="currentColor" />
              </svg>
              <span>Главная</span>
            </Link>
            <Link
              to="/admin/dashboard/bot-chats"
              className={`top-nav-item ${location.pathname.includes('/bot-chats') ? 'active' : ''}`}
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
              to="/admin/dashboard/logs"
              className={`top-nav-item ${location.pathname.includes('/logs') ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M4 4H16V16H4V4Z" stroke="currentColor" strokeWidth="2" />
                <path d="M4 8H16M4 12H12" stroke="currentColor" strokeWidth="2" />
              </svg>
              <span>Логи</span>
            </Link>
            <Link
              to="/admin/dashboard/database-schema"
              className={`top-nav-item ${location.pathname.includes('/database-schema') ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M4 4H16V16H4V4Z" stroke="currentColor" strokeWidth="2" />
                <path d="M4 8H16M4 12H16" stroke="currentColor" strokeWidth="2" />
              </svg>
              <span>База данных</span>
            </Link>
            <Link
              to="/admin/dashboard/dropdown-test"
              className={`top-nav-item ${location.pathname.includes('/dropdown-test') ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Тест меню</span>
            </Link>
            <Link to="/user/dashboard" className="top-nav-item">
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
          </>
        ) : (
          <>
            <Link
              to="/user/dashboard"
              className={`top-nav-item ${location.pathname === '/user/dashboard' ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z" fill="currentColor" />
              </svg>
              <span>Главная</span>
            </Link>
            <Link
              to="/user/dashboard/objects"
              className={`top-nav-item ${
                location.pathname.includes('/objects') && !location.pathname.includes('/create') ? 'active' : ''
              }`}
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
              <span>Объекты</span>
            </Link>
            <Link
              to="/user/dashboard/objects/create"
              className={`top-nav-item ${location.pathname.includes('/create') ? 'active' : ''}`}
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
            {user?.web_role === 'admin' && (
              <Link to="/admin/dashboard" className="top-nav-item">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2L2 7L10 12L18 7L10 2Z" fill="currentColor" />
                  <path
                    d="M2 13L10 18L18 13M2 10L10 15L18 10"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <span>Админ</span>
              </Link>
            )}
          </>
        )}
      </nav>

      <main className="app-main">{children}</main>

      {!isAdmin && (
        <nav className="bottom-nav mobile-bottom-nav">
          <Link
            to="/user/dashboard"
            className={`bottom-nav-icon-btn ${location.pathname === '/user/dashboard' ? 'active' : ''}`}
            aria-label="Главная"
          >
            <img src="/SVG/dashboard_down.svg" alt="Главная" width="24" height="24" style={{ filter: theme === 'dark' ? 'invert(1)' : 'none' }} />
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
          <MobileDropdownMenu objects={objects} type="objects" />
          <MobileDropdownMenu objects={objects} type="menu" />
        </nav>
      )}
      {isAdmin && (
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
          <Link
            to="/admin/dashboard/bot-chats"
            className={`nav-item ${location.pathname.includes('/bot-chats') ? 'active' : ''}`}
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
            to="/admin/dashboard/logs"
            className={`nav-item ${location.pathname.includes('/logs') ? 'active' : ''}`}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M4 4H16V16H4V4Z" stroke="currentColor" strokeWidth="2" />
              <path d="M4 8H16M4 12H12" stroke="currentColor" strokeWidth="2" />
            </svg>
            <span>Логи</span>
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
      )}
    </div>
  )
}


