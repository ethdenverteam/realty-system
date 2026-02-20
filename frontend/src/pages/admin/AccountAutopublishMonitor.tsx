import { useEffect, useState } from 'react'
import axios from 'axios'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import { formatSystemTime } from '../../utils/timezone'
import type { ApiErrorResponse } from '../../types/models'
import './AccountAutopublishMonitor.css'

interface AccountRow {
  account_id: number
  phone: string
  mode: string
  daily_limit: number
  today_publications: number
  last_used?: string | null
  last_error?: string | null
  queue: {
    pending: number
    processing: number
    failed: number
    completed: number
    flood_wait: number
  }
  next_pending?: {
    queue_id: number
    scheduled_time?: string | null
  } | null
}

interface QueueRow {
  queue_id: number
  object_id: string
  chat_id: number
  chat_title?: string | null
  account_id: number
  account_phone?: string | null
  status: string
  attempts: number
  scheduled_time?: string | null
  started_at?: string | null
  error_message?: string | null
}

interface MonitorResponse {
  success: boolean
  now_utc: string
  threshold_minutes: number
  summary: {
    active_accounts: number
    total_queues: number
    pending: number
    processing: number
    completed: number
    failed: number
    flood_wait: number
    ready_count: number
    stuck_count: number
    enabled_configs: number
    total_configs: number
  }
  accounts: AccountRow[]
  ready_queues: QueueRow[]
  stuck_queues: QueueRow[]
}

export default function AccountAutopublishMonitor(): JSX.Element {
  const [data, setData] = useState<MonitorResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [thresholdMinutes, setThresholdMinutes] = useState(5)
  const [resetting, setResetting] = useState(false)

  useEffect(() => {
    void loadData()
  }, [])

  const loadData = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<MonitorResponse>('/admin/dashboard/account-autopublish/monitor', {
        params: { threshold_minutes: String(thresholdMinutes) },
      })
      if (res.data.success) {
        setData(res.data)
      } else {
        setError('Не удалось загрузить мониторинг')
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка загрузки мониторинга')
      } else {
        setError('Ошибка загрузки мониторинга')
      }
    } finally {
      setLoading(false)
    }
  }

  const resetStuck = async (): Promise<void> => {
    const ok = window.confirm(`Сбросить все processing-задачи старше ${thresholdMinutes} минут?`)
    if (!ok) return

    try {
      setResetting(true)
      setActionMessage('')
      const res = await api.post('/admin/dashboard/account-autopublish/reset-stuck', {
        threshold_minutes: thresholdMinutes,
        max_attempts: 3,
      })
      const payload = res.data as {
        success: boolean
        total_found: number
        reset_to_pending: number
        marked_failed: number
        error?: string
      }
      if (payload.success) {
        setActionMessage(
          `Готово: найдено ${payload.total_found}, в pending: ${payload.reset_to_pending}, в failed: ${payload.marked_failed}`,
        )
        await loadData()
      } else {
        setError(payload.error || 'Ошибка сброса застрявших задач')
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка сброса застрявших задач')
      } else {
        setError('Ошибка сброса застрявших задач')
      }
    } finally {
      setResetting(false)
    }
  }

  return (
    <Layout title="Мониторинг аккаунтной автопубликации" isAdmin>
      <div className="account-monitor-page">
        {error && (
          <div className="alert alert-error" onClick={() => setError('')}>
            {error}
          </div>
        )}
        {actionMessage && <div className="alert alert-success">{actionMessage}</div>}

        <GlassCard className="monitor-controls-card">
          <div className="monitor-controls">
            <div className="control-group">
              <label>Порог застрявших задач (мин):</label>
              <input
                type="number"
                min={1}
                max={120}
                value={thresholdMinutes}
                onChange={(e) => setThresholdMinutes(Number(e.target.value || 5))}
                className="form-control"
              />
            </div>
            <button className="btn btn-secondary" onClick={() => void loadData()} disabled={loading}>
              Обновить
            </button>
            <button className="btn btn-danger" onClick={() => void resetStuck()} disabled={resetting || loading}>
              {resetting ? 'Сброс...' : 'Сбросить застрявшие'}
            </button>
          </div>
        </GlassCard>

        <div className="monitor-stats-grid">
          <GlassCard className="stat-card"><div className="stat-value">{data?.summary.active_accounts ?? '-'}</div><div className="stat-label">Активных аккаунтов</div></GlassCard>
          <GlassCard className="stat-card"><div className="stat-value">{data?.summary.total_queues ?? '-'}</div><div className="stat-label">Всего задач</div></GlassCard>
          <GlassCard className="stat-card"><div className="stat-value">{data?.summary.processing ?? '-'}</div><div className="stat-label">Processing</div></GlassCard>
          <GlassCard className="stat-card"><div className="stat-value">{data?.summary.stuck_count ?? '-'}</div><div className="stat-label">Застрявшие</div></GlassCard>
          <GlassCard className="stat-card"><div className="stat-value">{data?.summary.ready_count ?? '-'}</div><div className="stat-label">Готовые сейчас</div></GlassCard>
          <GlassCard className="stat-card"><div className="stat-value">{data?.summary.failed ?? '-'}</div><div className="stat-label">Failed</div></GlassCard>
        </div>

        <GlassCard className="monitor-section-card">
          <h2 className="card-title">Состояние аккаунтов</h2>
          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Аккаунт</th>
                    <th>Режим</th>
                    <th>Лимит сегодня</th>
                    <th>Очередь</th>
                    <th>Следующая pending</th>
                    <th>Последняя ошибка</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.accounts || []).map((acc) => (
                    <tr key={acc.account_id}>
                      <td>{acc.account_id} ({acc.phone})</td>
                      <td>{acc.mode}</td>
                      <td>{acc.today_publications}/{acc.daily_limit}</td>
                      <td>
                        p:{acc.queue.pending} pr:{acc.queue.processing} c:{acc.queue.completed} f:{acc.queue.failed} fw:{acc.queue.flood_wait}
                      </td>
                      <td>
                        {acc.next_pending ? `#${acc.next_pending.queue_id} ${formatSystemTime(acc.next_pending.scheduled_time || undefined)}` : '-'}
                      </td>
                      <td>{acc.last_error || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>

        <GlassCard className="monitor-section-card">
          <h2 className="card-title">Застрявшие задачи</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Queue</th>
                  <th>Объект</th>
                  <th>Аккаунт</th>
                  <th>Чат</th>
                  <th>Started</th>
                  <th>Attempts</th>
                  <th>Ошибка</th>
                </tr>
              </thead>
              <tbody>
                {(data?.stuck_queues || []).map((q) => (
                  <tr key={q.queue_id}>
                    <td>{q.queue_id}</td>
                    <td>{q.object_id}</td>
                    <td>{q.account_id} ({q.account_phone || '-'})</td>
                    <td>{q.chat_id} ({q.chat_title || '-'})</td>
                    <td>{formatSystemTime(q.started_at || undefined)}</td>
                    <td>{q.attempts}</td>
                    <td>{q.error_message || '-'}</td>
                  </tr>
                ))}
                {(data?.stuck_queues?.length || 0) === 0 && (
                  <tr>
                    <td colSpan={7} className="empty-row">Застрявших задач нет</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>
    </Layout>
  )
}


