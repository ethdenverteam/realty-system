import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import './Logs.css'

export default function AdminLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  useEffect(() => {
    loadLogs()
  }, [page])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const res = await api.get(`/admin/dashboard/logs/data?page=${page}&per_page=50`)
      setLogs(res.data.logs || [])
      setTotalPages(res.data.pagination?.pages || 1)
    } catch (err) {
      console.error('Error loading logs:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Просмотр логов" isAdmin>
      <div className="logs-page">
        <div className="card">
          <h2 className="card-title">Логи действий</h2>
          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : logs.length === 0 ? (
            <div className="empty-state">Нет логов</div>
          ) : (
            <>
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Время</th>
                      <th>Действие</th>
                      <th>Пользователь</th>
                      <th>Детали</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map(log => (
                      <tr key={log.log_id}>
                        <td>{new Date(log.created_at).toLocaleString('ru-RU')}</td>
                        <td><code>{log.action}</code></td>
                        <td>{log.user_id || 'System'}</td>
                        <td>
                          <small>
                            {log.details_json ? JSON.stringify(log.details_json).substring(0, 50) + '...' : '-'}
                          </small>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && (
                <div className="pagination">
                  <button 
                    className="btn btn-secondary"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Назад
                  </button>
                  <span>Страница {page} из {totalPages}</span>
                  <button 
                    className="btn btn-secondary"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    Вперед
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Layout>
  )
}

