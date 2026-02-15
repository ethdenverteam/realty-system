import { useEffect, useState } from 'react'
import axios from 'axios'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import type { ApiErrorResponse } from '../../types/models'
import './PublicationQueues.css'

interface PublicationQueue {
  queue_id: number
  object_id: string
  chat_id: number
  account_id?: number
  user_id?: number
  type: 'bot' | 'user'
  mode: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'retrying'
  scheduled_time?: string
  started_at?: string
  completed_at?: string
  attempts: number
  error_message?: string
  message_id?: string
  created_at: string
  object?: {
    object_id: string
    rooms_type?: string
    price?: number
    status?: string
  }
  chat?: {
    chat_id: number
    title: string
    telegram_chat_id: string
  }
  account?: {
    account_id: number
    phone: string
  }
}

interface QueuesResponse {
  success: boolean
  queues: PublicationQueue[]
  total: number
  offset: number
  limit: number
}

export default function PublicationQueues(): JSX.Element {
  const [queues, setQueues] = useState<PublicationQueue[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [queueType, setQueueType] = useState<'all' | 'bot' | 'user'>('all')
  const [status, setStatus] = useState<'all' | 'pending' | 'processing' | 'completed' | 'failed'>('all')
  const [total, setTotal] = useState(0)

  useEffect(() => {
    void loadQueues()
  }, [queueType, status])

  const loadQueues = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const params: Record<string, string> = {
        type: queueType,
        status: status,
        limit: '100',
        offset: '0',
      }
      const res = await api.get<QueuesResponse>('/admin/dashboard/publication-queues', { params })
      if (res.data.success) {
        setQueues(res.data.queues)
        setTotal(res.data.total)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка загрузки очередей')
      } else {
        setError('Ошибка загрузки очередей')
      }
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadgeClass = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'badge-success'
      case 'failed':
        return 'badge-danger'
      case 'processing':
        return 'badge-warning'
      case 'pending':
        return 'badge-secondary'
      case 'retrying':
        return 'badge-info'
      default:
        return 'badge-secondary'
    }
  }

  const getStatusLabel = (status: string): string => {
    const labels: Record<string, string> = {
      pending: 'Ожидание',
      processing: 'В процессе',
      completed: 'Завершено',
      failed: 'Ошибка',
      retrying: 'Повтор',
    }
    return labels[status] || status
  }

  return (
    <Layout title="Очереди публикации" isAdmin>
      <div className="publication-queues-page">
        {error && (
          <div className="alert alert-error" onClick={() => setError('')}>
            {error}
          </div>
        )}

        <GlassCard className="queues-filters-card">
          <div className="filters-row">
            <div className="filter-group">
              <label>Тип очереди:</label>
              <select
                value={queueType}
                onChange={(e) => setQueueType(e.target.value as 'all' | 'bot' | 'user')}
                className="form-control"
              >
                <option value="all">Все</option>
                <option value="bot">Бот</option>
                <option value="user">Пользователь</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Статус:</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as 'all' | 'pending' | 'processing' | 'completed' | 'failed')}
                className="form-control"
              >
                <option value="all">Все</option>
                <option value="pending">Ожидание</option>
                <option value="processing">В процессе</option>
                <option value="completed">Завершено</option>
                <option value="failed">Ошибка</option>
              </select>
            </div>
            <div className="filter-group">
              <button className="btn btn-secondary" onClick={() => void loadQueues()}>
                Обновить
              </button>
            </div>
          </div>
          <div className="queues-stats">
            <span>Всего: {total}</span>
            <span>Бот: {queues.filter(q => q.type === 'bot').length}</span>
            <span>Пользователь: {queues.filter(q => q.type === 'user').length}</span>
          </div>
        </GlassCard>

        <GlassCard className="queues-list-card">
          <h2 className="card-title">Очереди публикации</h2>
          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : queues.length === 0 ? (
            <div className="empty-state">
              <p>Очереди не найдены</p>
            </div>
          ) : (
            <div className="queues-table">
              <table>
                <thead>
                  <tr>
                    <th>Запланировано</th>
                    <th>Создано</th>
                    <th>Статус</th>
                    <th>Аккаунт</th>
                    <th>Объект</th>
                    <th>Чат</th>
                    <th>Ошибка</th>
                    <th>Попытки</th>
                    <th>Завершено</th>
                    <th>ID</th>
                    <th>Тип</th>
                  </tr>
                </thead>
                <tbody>
                  {queues.map((queue) => (
                    <tr key={queue.queue_id}>
                      <td>
                        {queue.scheduled_time
                          ? new Date(queue.scheduled_time).toLocaleString('ru-RU')
                          : '-'}
                      </td>
                      <td>
                        {queue.created_at
                          ? new Date(queue.created_at).toLocaleString('ru-RU')
                          : '-'}
                      </td>
                      <td>
                        <span className={`badge ${getStatusBadgeClass(queue.status)}`}>
                          {getStatusLabel(queue.status)}
                        </span>
                      </td>
                      <td>
                        {queue.account ? (
                          <div>{queue.account.phone}</div>
                        ) : queue.type === 'user' ? (
                          <span className="text-muted">-</span>
                        ) : (
                          <span className="text-muted">Бот</span>
                        )}
                      </td>
                      <td>
                        {queue.object ? (
                          <div>
                            <strong>{queue.object.object_id}</strong>
                            {queue.object.rooms_type && <div>{queue.object.rooms_type}</div>}
                            {queue.object.price && <div>{queue.object.price}тр</div>}
                          </div>
                        ) : (
                          queue.object_id
                        )}
                      </td>
                      <td>
                        {queue.chat ? (
                          <div>
                            <strong>{queue.chat.title}</strong>
                            <div className="text-muted">{queue.chat.telegram_chat_id}</div>
                          </div>
                        ) : (
                          `Chat ${queue.chat_id}`
                        )}
                      </td>
                      <td>
                        {queue.error_message ? (
                          <div className="error-message" title={queue.error_message}>
                            {queue.error_message.length > 50
                              ? `${queue.error_message.substring(0, 50)}...`
                              : queue.error_message}
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td>{queue.attempts}</td>
                      <td>
                        {queue.completed_at
                          ? new Date(queue.completed_at).toLocaleString('ru-RU')
                          : '-'}
                      </td>
                      <td>{queue.queue_id}</td>
                      <td>
                        <span className={`badge ${queue.type === 'bot' ? 'badge-primary' : 'badge-secondary'}`}>
                          {queue.type === 'bot' ? 'Бот' : 'Пользователь'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>
      </div>
    </Layout>
  )
}

