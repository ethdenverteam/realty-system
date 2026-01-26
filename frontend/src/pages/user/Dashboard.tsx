import axios from 'axios'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../../components/Layout'
import { useAuth } from '../../contexts/AuthContext'
import api from '../../utils/api'
import type { UserStats, ApiErrorResponse } from '../../types/models'
import './Dashboard.css'

export default function UserDashboard(): JSX.Element {
  const { user } = useAuth()
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    void loadStats()
  }, [])

  const loadStats = async (): Promise<void> => {
    try {
      const res = await api.get<UserStats>('/user/dashboard/stats')
      setStats(res.data)
    } catch (err: unknown) {
      setError('Ошибка загрузки данных')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Моя панель">
      <div className="dashboard-page">
        {error && <div className="alert alert-error">{error}</div>}

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{loading ? '-' : (stats?.objects_count ?? '-')}</div>
            <div className="stat-label">Мои объекты</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{loading ? '-' : (stats?.total_publications ?? '-')}</div>
            <div className="stat-label">Публикаций</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{loading ? '-' : (stats?.today_publications ?? '-')}</div>
            <div className="stat-label">Сегодня</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{loading ? '-' : (stats?.accounts_count ?? '-')}</div>
            <div className="stat-label">Аккаунтов</div>
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">Быстрые действия</h2>
          <div className="actions-grid">
            <Link to="/user/dashboard/objects/create" className="action-card">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M12 4V20M4 12H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span>Создать объект</span>
            </Link>
            <Link to="/user/dashboard/objects" className="action-card">
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
              <span>Мои объекты</span>
            </Link>
          </div>
        </div>

        {user?.web_role === 'admin' && (
          <div className="card">
            <h2 className="card-title">Админ функции</h2>
            <Link to="/admin/dashboard" className="action-card">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <path d="M12 8V12M12 16H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span>Админ панель</span>
            </Link>
          </div>
        )}
      </div>
    </Layout>
  )
}


