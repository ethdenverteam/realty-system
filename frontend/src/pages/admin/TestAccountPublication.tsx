import { useEffect, useState } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import type { RealtyObject } from '../../types/models'
import './TestAccountPublication.css'

interface TelegramAccount {
  account_id: number
  phone: string
  mode: string
  daily_limit: number
  is_active: boolean
  chats: Chat[]
}

interface Chat {
  chat_id: number
  telegram_chat_id: string
  title: string
  type: string
  is_active: boolean
}

export default function TestAccountPublication(): JSX.Element {
  const [objects, setObjects] = useState<RealtyObject[]>([])
  const [accounts, setAccounts] = useState<TelegramAccount[]>([])
  const [selectedObjectId, setSelectedObjectId] = useState<string>('')
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [publishing, setPublishing] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    void loadData()
  }, [])

  const loadData = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const [objectsRes, accountsRes] = await Promise.all([
        api.get<RealtyObject[]>('/admin/dashboard/test-account-publication/objects'),
        api.get<TelegramAccount[]>('/admin/dashboard/test-account-publication/accounts'),
      ])
      setObjects(objectsRes.data)
      setAccounts(accountsRes.data)
    } catch (err: unknown) {
      console.error('Error loading data:', err)
      const message =
        err instanceof Error
          ? err.message
          : 'Ошибка загрузки данных'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async (): Promise<void> => {
    if (!selectedObjectId || !selectedAccountId || !selectedChatId) {
      setError('Выберите объект, аккаунт и чат')
      return
    }

    try {
      setPublishing(true)
      setError('')
      setSuccess('')

      const res = await api.post<{ success: boolean; message_id?: number; message?: string }>(
        '/admin/dashboard/test-account-publication/publish',
        {
          object_id: selectedObjectId,
          account_id: selectedAccountId,
          chat_id: selectedChatId,
        }
      )

      if (res.data.success) {
        setSuccess(`Объект успешно опубликован! Message ID: ${res.data.message_id ?? 'N/A'}`)
        // Reset selections
        setSelectedObjectId('')
        setSelectedAccountId(null)
        setSelectedChatId(null)
      } else {
        setError(res.data.message ?? 'Ошибка публикации')
      }
    } catch (err: unknown) {
      console.error('Error publishing:', err)
      let message = 'Ошибка публикации'
      if (err instanceof Error) {
        message = err.message
      } else if (typeof err === 'object' && err !== null && 'response' in err) {
        const axiosError = err as { response?: { data?: { error?: string; details?: string } } }
        message = axiosError.response?.data?.error ?? message
        if (axiosError.response?.data?.details) {
          message += `: ${axiosError.response.data.details}`
        }
      }
      setError(message)
    } finally {
      setPublishing(false)
    }
  }

  const selectedAccount = accounts.find((acc) => acc.account_id === selectedAccountId)
  const availableChats = selectedAccount?.chats ?? []

  return (
    <Layout title="Проверка публикации через аккаунт" isAdmin>
      <div className="test-account-publication">
        <GlassCard>
          <h2 className="card-title">Тестовая публикация объекта через аккаунт</h2>
          <p style={{ fontSize: '14px', color: 'rgba(255, 255, 255, 0.7)', marginBottom: '20px' }}>
            Выберите объект, аккаунт и чат для тестовой публикации. Публикация будет выполнена
            согласно настройкам формата и содержимому объекта.
          </p>

          {loading && <div className="loading">Загрузка данных...</div>}

          {error && (
            <div className="alert alert-error" style={{ marginBottom: '20px' }}>
              {error}
            </div>
          )}

          {success && (
            <div className="alert alert-success" style={{ marginBottom: '20px' }}>
              {success}
            </div>
          )}

          {!loading && (
            <div className="publication-form">
              <div className="form-group">
                <label htmlFor="object-select">Объект недвижимости</label>
                <select
                  id="object-select"
                  value={selectedObjectId}
                  onChange={(e) => {
                    setSelectedObjectId(e.target.value)
                  }}
                  className="form-select"
                >
                  <option value="">-- Выберите объект --</option>
                  {objects.map((obj) => (
                    <option key={obj.object_id} value={obj.object_id}>
                      {obj.object_id} - {obj.rooms_type} - {obj.price}к - {obj.address ?? 'Без адреса'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="account-select">Telegram аккаунт</label>
                <select
                  id="account-select"
                  value={selectedAccountId ?? ''}
                  onChange={(e) => {
                    const accountId = e.target.value ? parseInt(e.target.value, 10) : null
                    setSelectedAccountId(accountId)
                    setSelectedChatId(null) // Reset chat when account changes
                  }}
                  className="form-select"
                >
                  <option value="">-- Выберите аккаунт --</option>
                  {accounts.map((acc) => (
                    <option key={acc.account_id} value={acc.account_id}>
                      {acc.phone} ({acc.mode}, лимит: {acc.daily_limit}/день)
                    </option>
                  ))}
                </select>
              </div>

              {selectedAccount && (
                <div className="form-group">
                  <label htmlFor="chat-select">Чат для публикации</label>
                  {availableChats.length === 0 ? (
                    <div className="alert alert-warning">
                      У выбранного аккаунта нет активных чатов
                    </div>
                  ) : (
                    <select
                      id="chat-select"
                      value={selectedChatId ?? ''}
                      onChange={(e) => {
                        const chatId = e.target.value ? parseInt(e.target.value, 10) : null
                        setSelectedChatId(chatId)
                      }}
                      className="form-select"
                    >
                      <option value="">-- Выберите чат --</option>
                      {availableChats.map((chat) => (
                        <option key={chat.chat_id} value={chat.chat_id}>
                          {chat.title} ({chat.type})
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              <div className="form-actions">
                <button
                  type="button"
                  onClick={handlePublish}
                  disabled={publishing || !selectedObjectId || !selectedAccountId || !selectedChatId}
                  className="btn btn-primary"
                >
                  {publishing ? 'Публикация...' : 'Опубликовать'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void loadData()
                  }}
                  className="btn btn-secondary"
                  disabled={loading}
                >
                  Обновить данные
                </button>
              </div>
            </div>
          )}
        </GlassCard>
      </div>
    </Layout>
  )
}

