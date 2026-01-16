import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './Layout.css'

export default function Layout({ children, title, headerActions, isAdmin = false }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  const handleLogout = () => {
    logout()
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
              onClick={handleLogout}
              aria-label="Выйти"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M7 17H3C2.44772 17 2 16.5523 2 16V4C2 3.44772 2.44772 3 3 3H7M14 14L17 10M17 10L14 6M17 10H7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        {children}
      </main>

      <nav className="bottom-nav">
        {isAdmin ? (
          <>
            <Link 
              to="/admin/dashboard" 
              className={`nav-item ${location.pathname === '/admin/dashboard' ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z" fill="currentColor"/>
              </svg>
              <span>Главная</span>
            </Link>
            <Link 
              to="/admin/dashboard/bot-chats" 
              className={`nav-item ${location.pathname.includes('/bot-chats') ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Чаты</span>
            </Link>
            <Link 
              to="/admin/dashboard/logs" 
              className={`nav-item ${location.pathname.includes('/logs') ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M4 4H16V16H4V4Z" stroke="currentColor" strokeWidth="2"/>
                <path d="M4 8H16M4 12H12" stroke="currentColor" strokeWidth="2"/>
              </svg>
              <span>Логи</span>
            </Link>
            <Link 
              to="/user/dashboard" 
              className="nav-item"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 10C12.7614 10 15 7.76142 15 5C15 2.23858 12.7614 0 10 0C7.23858 0 5 2.23858 5 5C5 7.76142 7.23858 10 10 10Z" fill="currentColor"/>
                <path d="M10 12C5.58172 12 2 14.2386 2 17V20H18V17C18 14.2386 14.4183 12 10 12Z" fill="currentColor"/>
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
                <path d="M3 10L9 4L9 9L17 9L17 11L9 11L9 16L3 10Z" fill="currentColor"/>
              </svg>
              <span>Главная</span>
            </Link>
            <Link 
              to="/user/dashboard/objects" 
              className={`nav-item ${location.pathname.includes('/objects') && !location.pathname.includes('/create') ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M2 5L10 9L18 5M2 15L10 19L18 15M2 10L10 14L18 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Объекты</span>
            </Link>
            <Link 
              to="/user/dashboard/objects/create" 
              className={`nav-item ${location.pathname.includes('/create') ? 'active' : ''}`}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 4V16M4 10H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <span>Создать</span>
            </Link>
            {user?.web_role === 'admin' && (
              <Link 
                to="/admin/dashboard" 
                className="nav-item"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2L2 7L10 12L18 7L10 2Z" fill="currentColor"/>
                  <path d="M2 13L10 18L18 13M2 10L10 15L18 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
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

