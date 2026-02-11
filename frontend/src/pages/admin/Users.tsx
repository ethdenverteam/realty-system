import axios from 'axios'
import { useEffect, useState } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import type { ApiErrorResponse } from '../../types/models'
import './Users.css'

interface User {
  user_id: number
  username?: string | null
  email?: string | null
  telegram_id?: number | null
  web_role: string
  bot_role?: string | null
  phone?: string | null
  created_at?: string
}

export default function AdminUsers(): JSX.Element {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState<number | null>(null)

  useEffect(() => {
    void loadUsers()
  }, [])

  const loadUsers = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<User[]>('/admin/dashboard/users')
      setUsers(res.data)
    } catch (err: unknown) {
      setError('Ошибка загрузки пользователей')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  const updateUserRole = async (userId: number, webRole: string, botRole: string): Promise<void> => {
    try {
      setSaving(userId)
      await api.put(`/admin/dashboard/users/${userId}/role`, {
        web_role: webRole,
        bot_role: botRole,
      })
      await loadUsers()
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        alert(err.response?.data?.error || 'Ошибка обновления роли')
      }
    } finally {
      setSaving(null)
    }
  }

  if (loading) {
    return (
      <Layout title="Управление пользователями" isAdmin>
        <div className="users-page">
          <div className="loading">Загрузка...</div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout title="Управление пользователями" isAdmin>
      <div className="users-page">
        {error && <div className="alert alert-error">{error}</div>}

        <GlassCard>
          <div className="card-header-row">
            <h2 className="card-title">Список пользователей</h2>
            <button onClick={() => void loadUsers()} className="btn btn-sm btn-secondary">
              Обновить
            </button>
          </div>

          <div className="users-table-container">
            <table className="users-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Имя пользователя</th>
                  <th>Email</th>
                  <th>Telegram ID</th>
                  <th>Телефон</th>
                  <th>Web роль</th>
                  <th>Bot роль</th>
                  <th>Дата создания</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.user_id}>
                    <td>{user.user_id}</td>
                    <td>{user.username || '-'}</td>
                    <td>{user.email || '-'}</td>
                    <td>{user.telegram_id || '-'}</td>
                    <td>{user.phone || '-'}</td>
                    <td>
                      <select
                        value={user.web_role}
                        onChange={(e) => {
                          void updateUserRole(user.user_id, e.target.value, user.bot_role || '')
                        }}
                        disabled={saving === user.user_id}
                        className="form-input form-input-sm"
                      >
                        <option value="user">user</option>
                        <option value="admin">admin</option>
                      </select>
                    </td>
                    <td>
                      <select
                        value={user.bot_role || ''}
                        onChange={(e) => {
                          void updateUserRole(user.user_id, user.web_role, e.target.value)
                        }}
                        disabled={saving === user.user_id}
                        className="form-input form-input-sm"
                      >
                        <option value="">-</option>
                        <option value="free">free</option>
                        <option value="premium">premium</option>
                      </select>
                    </td>
                    <td>
                      {user.created_at
                        ? new Date(user.created_at).toLocaleString('ru-RU')
                        : '-'}
                    </td>
                    <td>
                      {saving === user.user_id && <span className="text-muted">Сохранение...</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {users.length === 0 && (
            <div className="empty-state">Пользователи не найдены</div>
          )}
        </GlassCard>
      </div>
    </Layout>
  )
}

