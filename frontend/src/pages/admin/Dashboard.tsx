import axios from 'axios'
import { useEffect, useState } from 'react'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import type { ActionLogItem, AdminStats, LogsResponse, ApiErrorResponse } from '../../types/models'
import './Dashboard.css'

export default function AdminDashboard(): JSX.Element {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [recentActions, setRecentActions] = useState<ActionLogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    void loadData()
  }, [])

  const loadData = async (): Promise<void> => {
    try {
      setLoading(true)
      const [statsRes, logsRes] = await Promise.all([
        api.get<AdminStats>('/admin/dashboard/stats'),
        api.get<LogsResponse>('/admin/dashboard/logs/data?per_page=5'),
      ])

      setStats(statsRes.data)
      setRecentActions(logsRes.data.logs || [])
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
    <Layout title="Админ панель" isAdmin>
      <div className="dashboard-page">
        {error && <div className="alert alert-error">{error}</div>}

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats?.users_count ?? '-'}</div>
            <div className="stat-label">Пользователей</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats?.objects_count ?? '-'}</div>
            <div className="stat-label">Объектов</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats?.publications_today ?? '-'}</div>
            <div className="stat-label">Публикаций сегодня</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats?.accounts_count ?? '-'}</div>
            <div className="stat-label">Активных аккаунтов</div>
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">Быстрые действия</h2>
          <div className="actions-grid">
            <a href="/admin/dashboard/bot-chats" className="action-card">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                  d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>Управление чатами и районами бота</span>
            </a>
            <a href="/admin/dashboard/logs" className="action-card">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                  d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M14 2V8H20"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>Просмотр логов</span>
            </a>
            <a href="/admin/dashboard/users" className="action-card">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                  d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M12 11C14.2091 11 16 9.20914 16 7C16 4.79086 14.2091 3 12 3C9.79086 3 8 4.79086 8 7C8 9.20914 9.79086 11 12 11Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>Управление пользователями</span>
            </a>
            <a href="/user/dashboard" className="action-card">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                  d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M12 11C14.2091 11 16 9.20914 16 7C16 4.79086 14.2091 3 12 3C9.79086 3 8 4.79086 8 7C8 9.20914 9.79086 11 12 11Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>Пользовательский режим</span>
            </a>
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">Последние действия</h2>
          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : recentActions.length > 0 ? (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Время</th>
                    <th>Действие</th>
                    <th>Пользователь</th>
                  </tr>
                </thead>
                <tbody>
                  {recentActions.map((log) => (
                    <tr key={log.log_id}>
                      <td>{new Date(log.created_at).toLocaleString('ru-RU')}</td>
                      <td>
                        <code>{log.action}</code>
                      </td>
                      <td>{log.user_id || 'System'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">Нет действий</div>
          )}
        </div>
      </div>
    </Layout>
  )
}


