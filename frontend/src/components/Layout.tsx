import { Link, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
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
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()

  const handleLogout = (): void => {
    void logout()
  }

  return (
    <div className="app-layout">
      <header className={`app-header ${isAdmin ? 'admin' : ''}`}>
        <div className="header-content">
          <h1 className="header-title">{title}</h1>
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
            <button className="header-icon-btn" onClick={handleLogout} aria-label="Выйти">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path
                  d="M7 17H3C2.44772 17 2 16.5523 2 16V4C2 3.44772 2.44772 3 3 3H7M14 14L17 10M17 10L14 6M17 10H7"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">{children}</main>

      <nav className="bottom-nav">
        {isAdmin ? (
          <>
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
          </>
        ) : (
          <>
            <Link
              to="/user/dashboard"
              className={`nav-item ${location.pathname === '/user/dashboard' ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z" fill="currentColor" />
              </svg>
              <span>Главная</span>
            </Link>
            <Link
              to="/user/dashboard/objects"
              className={`nav-item ${
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
              className={`nav-item ${location.pathname.includes('/create') ? 'active' : ''}`}
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
              <Link to="/admin/dashboard" className="nav-item">
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
    </div>
  )
}


