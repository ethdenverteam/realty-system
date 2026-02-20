import axios from 'axios'
import { useEffect, useState } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
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
          <GlassCard className="stat-card">
            <div className="stat-value">{stats?.users_count ?? '-'}</div>
            <div className="stat-label">Пользователей</div>
          </GlassCard>
          <GlassCard className="stat-card">
            <div className="stat-value">{stats?.objects_count ?? '-'}</div>
            <div className="stat-label">Объектов</div>
          </GlassCard>
          <GlassCard className="stat-card">
            <div className="stat-value">{stats?.publications_today ?? '-'}</div>
            <div className="stat-label">Публикаций сегодня</div>
          </GlassCard>
          <GlassCard className="stat-card">
            <div className="stat-value">{stats?.accounts_count ?? '-'}</div>
            <div className="stat-label">Активных аккаунтов</div>
          </GlassCard>
        </div>

        <GlassCard>
          <h2 className="card-title">Страницы админ-панели</h2>
          <p style={{ fontSize: '14px', color: 'rgba(255, 255, 255, 0.7)', marginBottom: '15px' }}>
            Список всех доступных страниц админ-панели. Для добавления новой страницы добавьте её в массив ниже.
          </p>
          <div className="admin-pages-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '15px', marginTop: '15px' }}>
            {[
              { path: '/admin/dashboard', label: 'Главная', icon: '🏠' },
              { path: '/admin/dashboard/bot-chats', label: 'Управление чатами бота', icon: '💬' },
              { path: '/admin/dashboard/chat-lists', label: 'Списки чатов (подписки)', icon: '📂' },
              { path: '/admin/dashboard/logs', label: 'Просмотр логов', icon: '📋' },
              { path: '/admin/dashboard/publication-queues', label: 'Очереди публикаций', icon: '📤' },
              { path: '/admin/dashboard/account-autopublish-monitor', label: 'Мониторинг аккаунтной автопубликации', icon: '📈' },
              { path: '/admin/dashboard/test-account-publication', label: 'Проверка публикации аккаунт', icon: '🧪' },
              { path: '/admin/dashboard/settings', label: 'Настройки', icon: '⚙️' },
              { path: '/admin/dashboard/users', label: 'Управление пользователями', icon: '👥' },
              { path: '/admin/dashboard/database-schema', label: 'Структура БД', icon: '🗄️' },
              { path: '/admin/dashboard/dropdown-test', label: 'Тест Dropdown', icon: '🧪' },
              { path: '/admin/dashboard/test', label: 'Тесты компонентов', icon: '🧪' },
              { path: '/admin/dashboard/test/components', label: 'Тест компонентов (детально)', icon: '🧪' },
              { path: '/admin/dashboard/test/dropdown-test', label: 'Тест Dropdown (детально)', icon: '🧪' },
              { path: '/admin/dashboard/typescript-types', label: 'TypeScript типы', icon: '📝' },
              { path: '/admin/dashboard/mobx-store', label: 'MobX Store', icon: '📦' },
              // Добавьте новую страницу здесь, и она автоматически появится в списке
            ].map((page) => (
              <a
                key={page.path}
                href={page.path}
                className="admin-page-link"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '12px 15px',
                  borderRadius: '8px',
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                }}
              >
                <span style={{ fontSize: '20px' }}>{page.icon}</span>
                <span>{page.label}</span>
              </a>
            ))}
          </div>
        </GlassCard>

        <GlassCard>
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
        </GlassCard>
      </div>
    </Layout>
  )
}


