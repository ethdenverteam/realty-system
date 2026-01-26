import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../../components/Layout'
import './Logs.css'

type LogType = 'app' | 'errors' | 'bot' | 'bot_errors'

export default function AdminLogs(): JSX.Element {
  const [logs, setLogs] = useState<string[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [logType, setLogType] = useState<LogType>('app')
  const [error, setError] = useState('')
  const eventSourceRef = useRef<EventSource | null>(null)
  const logContainerRef = useRef<HTMLDivElement | null>(null)

  const logTypes: Array<{ value: LogType; label: string }> = [
    { value: 'app', label: 'Приложение (app.log)' },
    { value: 'errors', label: 'Ошибки (errors.log)' },
    { value: 'bot', label: 'Бот (bot.log)' },
    { value: 'bot_errors', label: 'Ошибки бота (bot_errors.log)' },
  ]

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  const startStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    setError('')
    setLogs([])
    setIsStreaming(true)

    const token = localStorage.getItem('jwt_token')
    const eventSource = new EventSource(
      `/api/logs/stream?type=${logType}&lines=100&token=${encodeURIComponent(token || '')}`,
    )

    eventSource.onmessage = (event: MessageEvent<string>) => {
      try {
        const data = JSON.parse(event.data) as { error?: string; line?: string }
        if (data.error) {
          setError(data.error)
          setIsStreaming(false)
          eventSource.close()
        } else if (data.line) {
          setLogs((prev) => {
            const newLogs = [...prev, data.line!]
            return newLogs.slice(-1000)
          })
        }
      } catch (err) {
        console.error('Error parsing log data:', err)
      }
    }

    eventSource.onerror = (err) => {
      console.error('EventSource error:', err)
      setError('Ошибка подключения к логам')
      setIsStreaming(false)
      eventSource.close()
    }

    eventSourceRef.current = eventSource
  }

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsStreaming(false)
  }

  const clearLogs = () => {
    setLogs([])
    setError('')
  }

  const handleLogTypeChange = (newType: LogType) => {
    if (isStreaming) {
      stopStreaming()
    }
    setLogType(newType)
    setLogs([])
  }

  const handleDownloadLogs = async () => {
    try {
      setError('')
      const token = localStorage.getItem('jwt_token')
      const downloadUrl = `/api/logs/download?token=${encodeURIComponent(token || '')}`

      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `realty_logs_${new Date().toISOString().slice(0, 10)}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      console.error('Error downloading logs:', err)
      setError('Ошибка при скачивании логов')
    }
  }

  return (
    <Layout
      title="Просмотр логов"
      isAdmin
      headerActions={
        <Link to="/admin/dashboard" className="btn btn-secondary">
          ← Назад в дашборд
        </Link>
      }
    >
      <div className="logs-page">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Терминал логов</h2>
            <div className="card-actions">
              <select
                className="form-input"
                value={logType}
                onChange={(e) => handleLogTypeChange(e.target.value as LogType)}
                disabled={isStreaming}
              >
                {logTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              {!isStreaming ? (
                <button className="btn btn-primary" onClick={startStreaming}>
                  ▶ Начать просмотр
                </button>
              ) : (
                <button className="btn btn-danger" onClick={stopStreaming}>
                  ⏸ Остановить
                </button>
              )}
              <button className="btn btn-secondary" onClick={clearLogs} disabled={isStreaming}>
                🗑 Очистить
              </button>
              <button
                className="btn btn-primary"
                onClick={handleDownloadLogs}
                title="Скачать все логи в ZIP архив"
              >
                ⬇️ Скачать логи
              </button>
            </div>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <div className="log-terminal-container" ref={logContainerRef}>
            {logs.length === 0 && !isStreaming && !error && (
              <div className="log-placeholder">
                Выберите тип лога и нажмите "Начать просмотр" для отображения последних 100 строк
              </div>
            )}
            {isStreaming && logs.length === 0 && <div className="log-placeholder">Загрузка логов...</div>}
            <div className="log-terminal">
              {logs.map((log, index) => (
                <div key={index} className="log-line">
                  {log}
                </div>
              ))}
            </div>
          </div>

          <div className="log-footer">
            <span className="log-stats">Строк: {logs.length} {isStreaming && '| Реал-тайм активен'}</span>
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => {
                if (logContainerRef.current) {
                  logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
                }
              }}
            >
              ↓ Вниз
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}


