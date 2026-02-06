import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import axios from 'axios'
import type { ApiErrorResponse } from '../../types/models'
import './TelegramAccounts.css'

interface TelegramAccount {
  account_id: number
  owner_id: number
  phone: string
  mode: string
  daily_limit: number
  is_active: boolean
  last_used: string | null
  last_error: string | null
  created_at: string
}

interface TelegramChat {
  id: string
  title: string
  type: string
  username: string | null
  members_count: number
}

export default function TelegramAccounts(): JSX.Element {
  const navigate = useNavigate()
  const [accounts, setAccounts] = useState<TelegramAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  
  // Chats state
  const [loadingChats, setLoadingChats] = useState<number | null>(null)
  const [accountChats, setAccountChats] = useState<Record<number, TelegramChat[]>>({})
  
  // Test message state
  const [testMessageAccount, setTestMessageAccount] = useState<number | null>(null)
  const [testMessageChatId, setTestMessageChatId] = useState('')
  const [testMessageText, setTestMessageText] = useState('Тестовое сообщение')
  const [sendingTestMessage, setSendingTestMessage] = useState(false)

  useEffect(() => {
    void loadAccounts()
  }, [])

  const loadAccounts = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<TelegramAccount[]>('/accounts')
      setAccounts(res.data)
    } catch (err: unknown) {
      setError('Ошибка загрузки аккаунтов')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      }
    } finally {
      setLoading(false)
    }
  }


  const loadAccountChats = async (accountId: number): Promise<void> => {
    try {
      setLoadingChats(accountId)
      setError('')
      const res = await api.get<{ success: boolean; chats: TelegramChat[] }>(`/accounts/${accountId}/chats`)
      
      if (res.data.success) {
        setAccountChats(prev => ({
          ...prev,
          [accountId]: res.data.chats
        }))
        setSuccess(`Загружено чатов: ${res.data.chats.length}`)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка загрузки чатов')
      } else {
        setError('Ошибка загрузки чатов')
      }
    } finally {
      setLoadingChats(null)
    }
  }

  const sendTestMessage = async (accountId: number): Promise<void> => {
    if (!testMessageChatId.trim()) {
      setError('Введите ID чата')
      return
    }

    try {
      setSendingTestMessage(true)
      setError('')
      const res = await api.post<{ success: boolean; message_id?: number; message?: string }>(`/accounts/${accountId}/test-message`, {
        chat_id: testMessageChatId.trim(),
        message: testMessageText.trim() || 'Тестовое сообщение'
      })
      
      if (res.data.success) {
        setSuccess(`Тестовое сообщение отправлено (ID: ${res.data.message_id})`)
        setTestMessageAccount(null)
        setTestMessageChatId('')
        void loadAccounts()
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка отправки сообщения')
      } else {
        setError('Ошибка отправки сообщения')
      }
    } finally {
      setSendingTestMessage(false)
    }
  }

  const toggleAccountActive = async (accountId: number, isActive: boolean): Promise<void> => {
    try {
      await api.put(`/accounts/${accountId}`, { is_active: !isActive })
      void loadAccounts()
      setSuccess('Настройки аккаунта обновлены')
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка обновления')
      }
    }
  }

  return (
    <Layout title="Telegram аккаунты">
      <div className="telegram-accounts-page">
        {error && (
          <div className="alert alert-error" onClick={() => setError('')}>
            {error}
          </div>
        )}
        {success && (
          <div className="alert alert-success" onClick={() => setSuccess('')}>
            {success}
          </div>
        )}

        <div className="accounts-header">
          <h2>Telegram аккаунты</h2>
          <button className="btn btn-primary" onClick={() => navigate('/user/dashboard/telegram-accounts/connect')}>
            + Подключить аккаунт
          </button>
        </div>

        {loading ? (
          <div className="loading">Загрузка...</div>
        ) : accounts.length === 0 ? (
          <GlassCard className="empty-state">
            <p>Нет подключенных аккаунтов</p>
            <button className="btn btn-primary" onClick={() => navigate('/user/dashboard/telegram-accounts/connect')}>
              Подключить первый аккаунт
            </button>
          </GlassCard>
        ) : (
          <div className="accounts-list">
            {accounts.map(account => (
              <GlassCard key={account.account_id} className="account-card">
                <div className="account-header">
                  <div className="account-info">
                    <h3>{account.phone}</h3>
                    <div className="account-meta">
                      <span className={`status ${account.is_active ? 'active' : 'inactive'}`}>
                        {account.is_active ? 'Активен' : 'Неактивен'}
                      </span>
                      <span>Режим: {account.mode}</span>
                      <span>Лимит: {account.daily_limit}/день</span>
                    </div>
                  </div>
                  <div className="account-actions">
                    <button
                      className={`btn btn-small ${account.is_active ? 'btn-warning' : 'btn-success'}`}
                      onClick={() => void toggleAccountActive(account.account_id, account.is_active)}
                    >
                      {account.is_active ? 'Деактивировать' : 'Активировать'}
                    </button>
                  </div>
                </div>
                
                {account.last_error && (
                  <div className="account-error">
                    Ошибка: {account.last_error}
                  </div>
                )}
                
                {account.last_used && (
                  <div className="account-last-used">
                    Последнее использование: {new Date(account.last_used).toLocaleString('ru-RU')}
                  </div>
                )}

                <div className="account-chats-section">
                  <div className="chats-header">
                    <h4>Чаты</h4>
                    <button
                      className="btn btn-small btn-secondary"
                      onClick={() => void loadAccountChats(account.account_id)}
                      disabled={loadingChats === account.account_id}
                    >
                      {loadingChats === account.account_id ? 'Загрузка...' : 'Загрузить чаты'}
                    </button>
                  </div>
                  
                  {accountChats[account.account_id] && (
                    <div className="chats-list">
                      {accountChats[account.account_id].length === 0 ? (
                        <p className="no-chats">Чаты не найдены</p>
                      ) : (
                        accountChats[account.account_id].map(chat => (
                          <div key={chat.id} className="chat-item">
                            <div className="chat-info">
                              <strong>{chat.title}</strong>
                              <span className="chat-type">{chat.type}</span>
                              {chat.username && <span>@{chat.username}</span>}
                              {chat.members_count > 0 && <span>{chat.members_count} участников</span>}
                            </div>
                            <button
                              className="btn btn-small btn-primary"
                              onClick={() => {
                                setTestMessageAccount(account.account_id)
                                setTestMessageChatId(chat.id)
                              }}
                            >
                              Тест
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </GlassCard>
            ))}
          </div>
        )}

        {/* Test Message Modal */}
        {testMessageAccount !== null && (
          <div className="modal-overlay" onClick={() => setTestMessageAccount(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Отправка тестового сообщения</h3>
                <button className="modal-close" onClick={() => setTestMessageAccount(null)}>×</button>
              </div>
              
              <div className="modal-body">
                <label>
                  ID чата
                  <input
                    type="text"
                    value={testMessageChatId}
                    onChange={(e) => setTestMessageChatId(e.target.value)}
                    placeholder="-1001234567890"
                    disabled={sendingTestMessage}
                  />
                </label>
                <label>
                  Текст сообщения
                  <textarea
                    value={testMessageText}
                    onChange={(e) => setTestMessageText(e.target.value)}
                    placeholder="Тестовое сообщение"
                    disabled={sendingTestMessage}
                    rows={3}
                  />
                </label>
                <div className="modal-actions">
                  <button
                    className="btn btn-secondary"
                    onClick={() => setTestMessageAccount(null)}
                    disabled={sendingTestMessage}
                  >
                    Отмена
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => void sendTestMessage(testMessageAccount)}
                    disabled={sendingTestMessage}
                  >
                    {sendingTestMessage ? 'Отправка...' : 'Отправить'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
