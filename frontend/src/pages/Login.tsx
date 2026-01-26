import { useState, useEffect } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../utils/api'
import './Login.css'

export default function Login(): JSX.Element | null {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [botLink, setBotLink] = useState('https://t.me/your_bot_username?start=getcode')
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    void loadBotInfo()
  }, [])

  const loadBotInfo = async (): Promise<void> => {
    try {
      const res = await api.get<{ username?: string }>('/auth/bot-info')
      if (res.data.username) {
        setBotLink(`https://t.me/${res.data.username}?start=getcode`)
      }
    } catch (err) {
      // Silently fail - use default link
      console.error('Failed to load bot info:', err)
    }
  }

  if (isAuthenticated) {
    return <Navigate to="/user/dashboard" replace />
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')

    if (code.length !== 6 || !/^\d{6}$/.test(code)) {
      setError('Код должен состоять из 6 цифр')
      return
    }

    setLoading(true)
    const result = await login(code)
    setLoading(false)

    if (result.success) {
      if (result.user.web_role === 'admin') {
        navigate('/admin/dashboard', { replace: true })
      } else {
        navigate('/user/dashboard', { replace: true })
      }
    } else {
      setError(result.error || 'Ошибка входа')
    }
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>Realty System</h1>
          <p className="login-subtitle">Введите код из Telegram бота</p>
        </div>

        <div className="login-info">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path
              d="M10 2C5.58172 2 2 5.58172 2 10C2 14.4183 5.58172 18 10 18C14.4183 18 18 14.4183 18 10C18 5.58172 14.4183 2 10 2ZM10 16C6.68629 16 4 13.3137 4 10C4 6.68629 6.68629 4 10 4C13.3137 4 16 6.68629 16 10C16 13.3137 13.3137 16 10 16Z"
              fill="currentColor"
            />
            <path
              d="M10 6C9.44772 6 9 6.44772 9 7C9 7.55228 9.44772 8 10 8C10.5523 8 11 7.55228 11 7C11 6.44772 10.5523 6 10 6Z"
              fill="currentColor"
            />
            <path
              d="M10 9C9.44772 9 9 9.44772 9 10V13C9 13.5523 9.44772 14 10 14C10.5523 14 11 13.5523 11 13V10C11 9.44772 10.5523 9 10 9Z"
              fill="currentColor"
            />
          </svg>
          <span>
            Получите 6-значный код, отправив команду{' '}
            <a
              href={botLink}
              target="_blank"
              rel="noopener noreferrer"
              className="login-bot-link"
            >
              <strong>/getcode</strong>
            </a>{' '}
            в Telegram боту
          </span>
        </div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="code" className="form-label">
              Код доступа
            </label>
            <input
              type="text"
              id="code"
              value={code}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setCode(e.target.value.replace(/\D/g, '').slice(0, 6))
              }
              placeholder="000000"
              maxLength={6}
              required
              autoFocus
              className="form-input"
              disabled={loading}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading || code.length !== 6}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  )
}


