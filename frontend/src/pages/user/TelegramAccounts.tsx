import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { useApiData } from '../../hooks/useApiData'
import { useApiMutation } from '../../hooks/useApiMutation'
import { getErrorMessage, logError } from '../../utils/errorHandler'
import api from '../../utils/api'
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
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  
  // Chats state
  const [loadingChats, setLoadingChats] = useState<number | null>(null)
  const [accountChats, setAccountChats] = useState<Record<number, TelegramChat[]>>({})
  
  // Test message state
  const [testMessageAccount, setTestMessageAccount] = useState<number | null>(null)
  const [testMessageChatId, setTestMessageChatId] = useState('')
  const [testMessageText, setTestMessageText] = useState('Тестовое сообщение')

  // Загрузка аккаунтов
  const { data: accounts, loading, reload: reloadAccounts } = useApiData<TelegramAccount[]>({
    url: '/accounts',
    errorContext: 'Loading accounts',
    defaultErrorMessage: 'Ошибка загрузки аккаунтов',
  })


  // Загрузка чатов для аккаунта
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
      const message = getErrorMessage(err, 'Ошибка загрузки чатов')
      setError(message)
      logError(err, 'Loading account chats')
    } finally {
      setLoadingChats(null)
    }
  }

  // Отправка тестового сообщения
  const [sendingTestMessage, setSendingTestMessage] = useState(false)
  const handleSendTestMessage = async (accountId: number): Promise<void> => {
    if (!testMessageChatId.trim()) {
      setError('Введите ID чата')
      return
    }

    try {
      setSendingTestMessage(true)
      setError('')
      const res = await api.post<{ success: boolean; message_id?: number; message?: string }>(`/accounts/${accountId}/test-message`, {
        chat_id: testMessageChatId.trim(),
        message: testMessageText.trim() || 'Тестовое сообщение',
      })
      
      if (res.data.success) {
        setSuccess(`Тестовое сообщение отправлено (ID: ${res.data.message_id || 'N/A'})`)
        setTestMessageAccount(null)
        setTestMessageChatId('')
        void reloadAccounts()
      }
    } catch (err: unknown) {
      const message = getErrorMessage(err, 'Ошибка отправки сообщения')
      setError(message)
      logError(err, 'Sending test message')
    } finally {
      setSendingTestMessage(false)
    }
  }

  // Переключение активности аккаунта
  const handleToggleAccountActive = async (accountId: number, isActive: boolean): Promise<void> => {
    try {
      setError('')
      await api.put(`/accounts/${accountId}`, { is_active: !isActive })
      setSuccess('Настройки аккаунта обновлены')
      void reloadAccounts()
    } catch (err: unknown) {
      const message = getErrorMessage(err, 'Ошибка обновления')
      setError(message)
      logError(err, 'Toggling account active')
    }
  }

  // Изменение режима аккаунта
  const handleModeChange = async (accountId: number, mode: string): Promise<void> => {
    try {
      setError('')
      await api.put(`/accounts/${accountId}`, { mode })
      setSuccess('Режим аккаунта обновлен')
      void reloadAccounts()
    } catch (err: unknown) {
      const message = getErrorMessage(err, 'Ошибка обновления режима')
      setError(message)
      logError(err, 'Changing account mode')
    }
  }

  // Удаление аккаунта
  const handleDeleteAccount = async (accountId: number): Promise<void> => {
    const confirmed = window.confirm(
      'Вы уверены, что хотите ПОЛНОСТЬЮ УДАЛИТЬ аккаунт? Будет удалена сессия и все связанные с ним чаты.'
    )
    if (!confirmed) return

    try {
      setError('')
      const res = await api.delete<{ success: boolean; error?: string }>(`/accounts/${accountId}`)
      if (!res.data.success && res.data.error) {
        setError(res.data.error)
        return
      }
      setSuccess('Аккаунт и связанные с ним чаты успешно удалены')
      void reloadAccounts()
    } catch (err: unknown) {
      const message = getErrorMessage(err, 'Ошибка удаления аккаунта')
      setError(message)
      logError(err, 'Deleting account')
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
        ) : !accounts || accounts.length === 0 ? (
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
                      <span>
                        Режим:{' '}
                        <select
                          value={account.mode}
                          onChange={(e) => handleModeChange(account.account_id, e.target.value)}
                          style={{ marginLeft: '4px', padding: '2px 4px', fontSize: '14px' }}
                        >
                          <option value="safe">Safe</option>
                          <option value="normal">Normal</option>
                          <option value="aggressive">Aggressive</option>
                          <option value="smart">Smart</option>
                          <option value="fix">Fix</option>
                        </select>
                      </span>
                      <span>Лимит: {account.daily_limit}/день</span>
                    </div>
                  </div>
                  <div className="account-actions">
                    <button
                      className={`btn btn-small ${account.is_active ? 'btn-warning' : 'btn-success'}`}
                      onClick={() => handleToggleAccountActive(account.account_id, account.is_active)}
                    >
                      {account.is_active ? 'Деактивировать' : 'Активировать'}
                    </button>
                    <button
                      className="btn btn-small btn-danger"
                      onClick={() => handleDeleteAccount(account.account_id)}
                    >
                      ПОЛНОСТЬЮ УДАЛИТЬ
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
                    onClick={() => testMessageAccount && handleSendTestMessage(testMessageAccount)}
                    disabled={sendingTestMessage || !testMessageAccount}
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
