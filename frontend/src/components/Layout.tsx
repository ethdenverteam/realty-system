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
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M9 22V12H15V22"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </Link>
              <Link
                to="/user/dashboard/settings"
                className="header-icon-btn"
                aria-label="Настройки"
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M19.4 15C19.2669 15.3016 19.2272 15.6362 19.286 15.9606C19.3448 16.285 19.4995 16.5843 19.73 16.82L19.79 16.88C19.976 17.0657 20.1235 17.2863 20.2241 17.5291C20.3248 17.7719 20.3766 18.0322 20.3766 18.295C20.3766 18.5578 20.3248 18.8181 20.2241 19.0609C20.1235 19.3037 19.976 19.5243 19.79 19.71L19.73 19.77C19.4943 20.0005 19.195 20.1552 18.8706 20.214C18.5462 20.2728 18.2116 20.2331 17.91 20.1C17.6084 19.9669 17.3534 19.7462 17.18 19.47L17.12 19.41C16.9972 19.2038 16.8362 19.0272 16.6464 18.8904C16.4566 18.7536 16.242 18.6596 16.015 18.615L15.945 18.6C15.682 18.555 15.409 18.555 15.146 18.6L15.076 18.615C14.849 18.6596 14.6344 18.7536 14.4446 18.8904C14.2548 19.0272 14.0938 19.2038 13.971 19.41L13.911 19.47C13.7376 19.7462 13.4826 19.9669 13.181 20.1C12.8794 20.2331 12.5448 20.2728 12.2204 20.214C11.896 20.1552 11.5967 20.0005 11.366 19.77L11.306 19.71C11.12 19.5243 10.9725 19.3037 10.8719 19.0609C10.7712 18.8181 10.7194 18.5578 10.7194 18.295C10.7194 18.0322 10.7712 17.7719 10.8719 17.5291C10.9725 17.2863 11.12 17.0657 11.306 16.88L11.366 16.82C11.5967 16.5843 11.896 16.285 12.2204 16.2262C12.5448 16.1674 12.8794 16.2071 13.181 16.34C13.4826 16.4731 13.7376 16.6938 13.911 16.97L13.971 17.03C14.0938 17.2362 14.2548 17.4128 14.4446 17.5496C14.6344 17.6864 14.849 17.7804 15.076 17.825L15.146 17.84C15.409 17.885 15.682 17.885 15.945 17.84L16.015 17.825C16.242 17.7804 16.4566 17.6864 16.6464 17.5496C16.8362 17.4128 16.9972 17.2362 17.12 17.03L17.18 16.97C17.3534 16.6938 17.6084 16.4731 17.91 16.34C18.2116 16.2071 18.5462 16.1674 18.8706 16.2262C19.195 16.285 19.4943 16.5843 19.73 16.82L19.79 16.88C19.976 17.0657 20.1235 17.2863 20.2241 17.5291C20.3248 17.7719 20.3766 18.0322 20.3766 18.295C20.3766 18.5578 20.3248 18.8181 20.2241 19.0609C20.1235 19.3037 19.976 19.5243 19.79 19.71L19.73 19.77C19.4943 20.0005 19.195 20.1552 18.8706 20.214C18.5462 20.2728 18.2116 20.2331 17.91 20.1H17.82C17.6084 20.2331 17.3534 20.4538 17.18 20.73L17.12 20.79C16.9972 20.9962 16.8362 21.1728 16.6464 21.3096C16.4566 21.4464 16.242 21.5404 16.015 21.585L15.945 21.6C15.682 21.645 15.409 21.645 15.146 21.6L15.076 21.585C14.849 21.5404 14.6344 21.4464 14.4446 21.3096C14.2548 21.1728 14.0938 20.9962 13.971 20.79L13.911 20.73C13.7376 20.4538 13.4826 20.2331 13.181 20.1C12.8794 19.9669 12.5448 19.9272 12.2204 19.986C11.896 20.0448 11.5967 20.1995 11.366 20.43L11.306 20.49C11.12 20.6757 10.9725 20.8963 10.8719 21.1391C10.7712 21.3819 10.7194 21.6422 10.7194 21.905C10.7194 22.1678 10.7712 22.4281 10.8719 22.6709C10.9725 22.9137 11.12 23.1343 11.306 23.32L11.366 23.38C11.5967 23.6105 11.896 23.7652 12.2204 23.824C12.5448 23.8828 12.8794 23.8431 13.181 23.71C13.4826 23.5769 13.7376 23.3562 13.911 23.08L13.971 23.02C14.0938 22.8138 14.2548 22.6372 14.4446 22.5004C14.6344 22.3636 14.849 22.2696 15.076 22.225L15.146 22.21C15.409 22.165 15.682 22.165 15.945 22.21L16.015 22.225C16.242 22.2696 16.4566 22.3636 16.6464 22.5004C16.8362 22.6372 16.9972 22.8138 17.12 23.02L17.18 23.08C17.3534 23.3562 17.6084 23.5769 17.91 23.71C18.2116 23.8431 18.5462 23.8828 18.8706 23.824C19.195 23.7652 19.4943 23.6105 19.73 23.38L19.79 23.32C19.976 23.1343 20.1235 22.9137 20.2241 22.6709C20.3248 22.4281 20.3766 22.1678 20.3766 21.905C20.3766 21.6422 20.3248 21.3819 20.2241 21.1391C20.1235 20.8963 19.976 20.6757 19.79 20.49L19.73 20.43C19.4943 20.1995 19.195 20.0448 18.8706 19.986C18.5462 19.9272 18.2116 19.9669 17.91 20.1L17.82 20.1C17.6084 20.2331 17.3534 20.4538 17.18 20.73L17.12 20.79C16.9972 20.9962 16.8362 21.1728 16.6464 21.3096C16.4566 21.4464 16.242 21.5404 16.015 21.585L15.945 21.6C15.682 21.645 15.409 21.645 15.146 21.6L15.076 21.585C14.849 21.5404 14.6344 21.4464 14.4446 21.3096C14.2548 21.1728 14.0938 20.9962 13.971 20.79L13.911 20.73C13.7376 20.4538 13.4826 20.2331 13.181 20.1C12.8794 19.9669 12.5448 19.9272 12.2204 19.986C11.896 20.0448 11.5967 20.1995 11.366 20.43L11.306 20.49C11.12 20.6757 10.9725 20.8963 10.8719 21.1391C10.7712 21.3819 10.7194 21.6422 10.7194 21.905C10.7194 22.1678 10.7712 22.4281 10.8719 22.6709C10.9725 22.9137 11.12 23.1343 11.306 23.32L11.366 23.38C11.5967 23.6105 11.896 23.7652 12.2204 23.824C12.5448 23.8828 12.8794 23.8431 13.181 23.71C13.4826 23.5769 13.7376 23.3562 13.911 23.08L13.971 23.02C14.0938 22.8138 14.2548 22.6372 14.4446 22.5004C14.6344 22.3636 14.849 22.2696 15.076 22.225L15.146 22.21C15.409 22.165 15.682 22.165 15.945 22.21L16.015 22.225C16.242 22.2696 16.4566 22.3636 16.6464 22.5004C16.8362 22.6372 16.9972 22.8138 17.12 23.02L17.18 23.08C17.3534 23.3562 17.6084 23.5769 17.91 23.71C18.2116 23.8431 18.5462 23.8828 18.8706 23.824C19.195 23.7652 19.4943 23.6105 19.73 23.38L19.79 23.32C19.976 23.1343 20.1235 22.9137 20.2241 22.6709C20.3248 22.4281 20.3766 22.1678 20.3766 21.905C20.3766 21.6422 20.3248 21.3819 20.2241 21.1391C20.1235 20.8963 19.976 20.6757 19.79 20.49L19.73 20.43C19.4943 20.1995 19.195 20.0448 18.8706 19.986C18.5462 19.9272 18.2116 19.9669 17.91 20.1H17.82"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
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
          <div className="bottom-nav-left"></div>
          <div className="bottom-nav-right">
            <Link
              to="/user/dashboard/objects"
              className="bottom-nav-icon-btn"
              aria-label="Все объекты"
            >
              <span style={{ fontSize: '24px' }}>📋</span>
            </Link>
            <MobileDropdownMenu objects={objects} />
          </div>
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


