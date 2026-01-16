import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import './Logs.css'

export default function AdminLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [logType, setLogType] = useState('app')
  const [error, setError] = useState('')
  const eventSourceRef = useRef(null)
  const logContainerRef = useRef(null)

  const logTypes = [
    { value: 'app', label: 'Приложение (app.log)' },
    { value: 'errors', label: 'Ошибки (errors.log)' },
    { value: 'bot', label: 'Бот (bot.log)' },
    { value: 'bot_errors', label: 'Ошибки бота (bot_errors.log)' }
  ]

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  useEffect(() => {
    // Auto-scroll to bottom when new logs arrive
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

    // Create EventSource for Server-Sent Events
    // Get auth token from localStorage
    const token = localStorage.getItem('jwt_token')
    const eventSource = new EventSource(
      `/api/logs/stream?type=${logType}&lines=100&token=${encodeURIComponent(token || '')}`
    )

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.error) {
          setError(data.error)
          setIsStreaming(false)
          eventSource.close()
        } else if (data.line) {
          setLogs(prev => {
            const newLogs = [...prev, data.line]
            // Keep only last 1000 lines to prevent memory issues
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

  const handleLogTypeChange = (newType) => {
    if (isStreaming) {
      stopStreaming()
    }
    setLogType(newType)
    setLogs([])
  }

  const handleDownloadLogs = async () => {
    try {
      setError('')
      // Get auth token
      const token = localStorage.getItem('jwt_token')
      
      // Create download link
      const downloadUrl = `/api/logs/download?token=${encodeURIComponent(token || '')}`
      
      // Create temporary link and trigger download
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `realty_logs_${new Date().toISOString().slice(0, 10)}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Show success message (optional - you can add a success state)
      console.log('Логи скачиваются...')
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
                onChange={(e) => handleLogTypeChange(e.target.value)}
                disabled={isStreaming}
              >
                {logTypes.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              {!isStreaming ? (
                <button 
                  className="btn btn-primary"
                  onClick={startStreaming}
                >
                  ▶ Начать просмотр
                </button>
              ) : (
                <button 
                  className="btn btn-danger"
                  onClick={stopStreaming}
                >
                  ⏸ Остановить
                </button>
              )}
              <button 
                className="btn btn-secondary"
                onClick={clearLogs}
                disabled={isStreaming}
              >
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
          
          {error && (
            <div className="alert alert-error">{error}</div>
          )}

          <div className="log-terminal-container" ref={logContainerRef}>
            {logs.length === 0 && !isStreaming && !error && (
              <div className="log-placeholder">
                Выберите тип лога и нажмите "Начать просмотр" для отображения последних 100 строк
              </div>
            )}
            {isStreaming && logs.length === 0 && (
              <div className="log-placeholder">
                Загрузка логов...
              </div>
            )}
            <div className="log-terminal">
              {logs.map((log, index) => (
                <div key={index} className="log-line">
                  {log}
                </div>
              ))}
            </div>
          </div>

          <div className="log-footer">
            <span className="log-stats">
              Строк: {logs.length} {isStreaming && '| Реал-тайм активен'}
            </span>
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
