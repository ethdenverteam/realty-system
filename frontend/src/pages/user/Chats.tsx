import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import axios from 'axios'
import type { ApiErrorResponse } from '../../types/models'
import './Chats.css'

interface TelegramAccount {
  account_id: number
  phone: string
  is_active: boolean
  last_used?: string
  last_error?: string
}

interface CachedChat {
  chat_id: number
  telegram_chat_id: string
  title: string
  type: string
  owner_account_id: number
  members_count: number
  cached_at?: string
}

interface RealtyObject {
  object_id: string
  rooms_type?: string
  price: number
  status: string
}

interface ChatGroup {
  group_id: number
  name: string
  description?: string
  chat_ids: number[]
}

export default function Chats(): JSX.Element {
  const [accounts, setAccounts] = useState<TelegramAccount[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [chats, setChats] = useState<CachedChat[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [testMessageChatId, setTestMessageChatId] = useState<number | null>(null)
  const [sendingTest, setSendingTest] = useState(false)
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null)
  const [objects, setObjects] = useState<RealtyObject[]>([])
  const [publishing, setPublishing] = useState(false)
  const [search, setSearch] = useState('')
  const [showCreateGroupModal, setShowCreateGroupModal] = useState(false)
  const [selectedChatsForGroup, setSelectedChatsForGroup] = useState<number[]>([])
  const [groupName, setGroupName] = useState('')
  const [groupDescription, setGroupDescription] = useState('')
  const [creatingGroup, setCreatingGroup] = useState(false)

  useEffect(() => {
    void loadAccounts()
  }, [])

  useEffect(() => {
    if (selectedAccountId) {
      void loadChats(selectedAccountId, search)
    } else {
      setChats([])
    }
  }, [selectedAccountId, search])

  const loadAccounts = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<TelegramAccount[]>('/accounts')
      setAccounts(res.data.filter(acc => acc.is_active))
      if (res.data.length > 0 && !selectedAccountId) {
        setSelectedAccountId(res.data[0].account_id)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка загрузки аккаунтов')
      } else {
        setError('Ошибка загрузки аккаунтов')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadChats = async (accountId: number, searchQuery?: string): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const params: Record<string, string | number> = {
        account_id: accountId,
        owner_type: 'user'
      }
      if (searchQuery && searchQuery.trim() !== '') {
        params.search = searchQuery.trim()
      }
      const res = await api.get<CachedChat[]>('/chats', {
        params
      })
      setChats(res.data)
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка загрузки чатов')
      } else {
        setError('Ошибка загрузки чатов')
      }
    } finally {
      setLoading(false)
    }
  }

  const refreshChats = async (): Promise<void> => {
    if (!selectedAccountId) return
    
    try {
      setRefreshing(true)
      setError('')
      const res = await api.get<{ success: boolean; chats: CachedChat[] }>(`/accounts/${selectedAccountId}/chats`)
      if (res.data.success) {
        setSuccess('Чаты обновлены')
        setTimeout(() => setSuccess(''), 3000)
        // Reload cached chats
        await loadChats(selectedAccountId, search)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка обновления чатов')
      } else {
        setError('Ошибка обновления чатов')
      }
    } finally {
      setRefreshing(false)
    }
  }

  const sendTestMessage = async (chatId: number): Promise<void> => {
    if (!selectedAccountId) return
    
    try {
      setSendingTest(true)
      setError('')
      const res = await api.post<{ success: boolean; message_id?: number }>(`/accounts/${selectedAccountId}/test-message`, {
        chat_id: chatId.toString(),
        message: 'Тестовое сообщение'
      })
      if (res.data.success) {
        setSuccess('Тестовое сообщение отправлено')
        setTimeout(() => setSuccess(''), 3000)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка отправки тестового сообщения')
      } else {
        setError('Ошибка отправки тестового сообщения')
      }
    } finally {
      setSendingTest(false)
      setTestMessageChatId(null)
    }
  }

  const loadObjects = async (): Promise<void> => {
    try {
      const res = await api.get<{ objects: RealtyObject[] }>('/objects')
      setObjects(res.data.objects.filter(obj => obj.status !== 'архив'))
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка загрузки объектов')
      } else {
        setError('Ошибка загрузки объектов')
      }
    }
  }

  const openPublishModal = async (chatId: number): Promise<void> => {
    setSelectedChatId(chatId)
    await loadObjects()
    setShowPublishModal(true)
  }

  const publishObject = async (objectId: string): Promise<void> => {
    if (!selectedAccountId || !selectedChatId) return
    
    try {
      setPublishing(true)
      setError('')
      const res = await api.post<{ success: boolean; message_id?: number }>('/objects/publish-via-account', {
        object_id: objectId,
        account_id: selectedAccountId,
        chat_id: selectedChatId
      })
      if (res.data.success) {
        setSuccess('Объект успешно опубликован')
        setTimeout(() => {
          setSuccess('')
          setShowPublishModal(false)
          setSelectedChatId(null)
        }, 3000)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка публикации объекта')
      } else {
        setError('Ошибка публикации объекта')
      }
    } finally {
      setPublishing(false)
    }
  }

  const openCreateGroupModal = (): void => {
    setSelectedChatsForGroup([])
    setGroupName('')
    setGroupDescription('')
    setShowCreateGroupModal(true)
  }

  const createChatGroup = async (): Promise<void> => {
    if (!groupName.trim()) {
      setError('Введите название группы')
      return
    }
    if (selectedChatsForGroup.length === 0) {
      setError('Выберите хотя бы один чат')
      return
    }

    try {
      setCreatingGroup(true)
      setError('')
      const res = await api.post<{ success: boolean; group: ChatGroup }>('/chats/groups', {
        name: groupName.trim(),
        description: groupDescription.trim() || undefined,
        chat_ids: selectedChatsForGroup
      })
      if (res.data.success) {
        setSuccess('Группа чатов создана')
        setTimeout(() => {
          setSuccess('')
          setShowCreateGroupModal(false)
          setSelectedChatsForGroup([])
          setGroupName('')
          setGroupDescription('')
        }, 3000)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка создания группы')
      } else {
        setError('Ошибка создания группы')
      }
    } finally {
      setCreatingGroup(false)
    }
  }

  return (
    <Layout title="Чаты">
      <div className="chats-page">
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

        <GlassCard className="chats-card">
          <div className="card-header-row">
            <h2 className="card-title">
              Чаты из аккаунтов
              {selectedAccountId && !loading && (
                <span className="chats-count"> ({chats.length})</span>
              )}
            </h2>
            <div className="chats-actions">
              <div className="chats-actions-row">
                <select
                  value={selectedAccountId || ''}
                  onChange={(e) => setSelectedAccountId(Number(e.target.value))}
                  className="select-account form-input form-input-sm"
                  disabled={loading}
                >
                  <option value="">Выберите аккаунт</option>
                  {accounts.map(acc => (
                    <option key={acc.account_id} value={acc.account_id}>
                      {acc.phone}
                    </option>
                  ))}
                </select>
                {selectedAccountId && (
                  <>
                    <button
                      className="btn btn-secondary"
                      onClick={() => void refreshChats()}
                      disabled={refreshing}
                    >
                      {refreshing ? 'Обновление...' : 'Обновить чаты'}
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={openCreateGroupModal}
                      disabled={chats.length === 0}
                    >
                      Создать группу
                    </button>
                  </>
                )}
              </div>
              {selectedAccountId && (
                <div className="chats-actions-row">
                  <input
                    type="text"
                    className="form-input form-input-sm chats-search-input"
                    placeholder="Поиск по чатам..."
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value)
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          {loading && <div className="loading">Загрузка...</div>}

          {!loading && selectedAccountId && chats.length === 0 && (
            <div className="empty-state">
              <p>Чаты не найдены. Нажмите "Обновить чаты" для загрузки или измените параметры поиска.</p>
            </div>
          )}

          {!loading && chats.length > 0 && (
            <div className="objects-list chats-list">
              {chats.map(chat => (
                <div key={chat.chat_id} className="object-card compact chat-item">
                  <div className="object-details-compact single-line">
                    <label className="chat-select-checkbox">
                      <input
                        type="checkbox"
                        checked={selectedChatsForGroup.includes(chat.chat_id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedChatsForGroup(prev => [...prev, chat.chat_id])
                          } else {
                            setSelectedChatsForGroup(prev => prev.filter(id => id !== chat.chat_id))
                          }
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </label>
                    <span className="object-detail-item">
                      {chat.title}
                    </span>
                  </div>
                  <div className="chat-actions">
                    <button
                      className="btn btn-small btn-secondary"
                      onClick={() => {
                        setTestMessageChatId(chat.chat_id)
                        void sendTestMessage(chat.telegram_chat_id as unknown as number)
                      }}
                      disabled={sendingTest && testMessageChatId === chat.chat_id}
                    >
                      {sendingTest && testMessageChatId === chat.chat_id ? 'Отправка...' : 'Отправить тест'}
                    </button>
                    <button
                      className="btn btn-small btn-primary"
                      onClick={() => void openPublishModal(chat.chat_id)}
                    >
                      Опубликовать объект
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        {showPublishModal && (
          <div className="modal-overlay" onClick={() => setShowPublishModal(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Выберите объект для публикации</h3>
                <button className="modal-close" onClick={() => setShowPublishModal(false)}>×</button>
              </div>
              <div className="modal-body">
                {objects.length === 0 ? (
                  <p>Нет доступных объектов</p>
                ) : (
                  <div className="objects-list">
                    {objects.map(obj => (
                      <div key={obj.object_id} className="object-item" onClick={() => void publishObject(obj.object_id)}>
                        <div className="object-info">
                          <strong>{obj.object_id}</strong>
                          {obj.rooms_type && <span>{obj.rooms_type}</span>}
                          {obj.price > 0 && <span>{obj.price} тыс. руб.</span>}
                        </div>
                        <button
                          className="btn btn-small btn-primary"
                          disabled={publishing}
                        >
                          {publishing ? 'Публикация...' : 'Опубликовать'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {showCreateGroupModal && (
          <div className="modal-overlay" onClick={() => setShowCreateGroupModal(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Создать группу чатов</h3>
                <button className="modal-close" onClick={() => setShowCreateGroupModal(false)}>×</button>
              </div>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Название группы *</label>
                  <input
                    type="text"
                    className="form-control"
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    placeholder="Например: Основные чаты"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Описание (необязательно)</label>
                  <textarea
                    className="form-control"
                    value={groupDescription}
                    onChange={(e) => setGroupDescription(e.target.value)}
                    placeholder="Описание группы"
                    rows={3}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Выбранные чаты: {selectedChatsForGroup.length}</label>
                  {selectedChatsForGroup.length === 0 ? (
                    <p className="text-muted">Выберите чаты из списка выше</p>
                  ) : (
                    <ul className="selected-chats-list">
                      {chats.filter(c => selectedChatsForGroup.includes(c.chat_id)).map(chat => (
                        <li key={chat.chat_id}>
                          {chat.title}
                          <button
                            type="button"
                            className="btn btn-small btn-link"
                            onClick={() => setSelectedChatsForGroup(prev => prev.filter(id => id !== chat.chat_id))}
                          >
                            Убрать
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              <div className="modal-actions">
                <button className="btn btn-secondary" onClick={() => setShowCreateGroupModal(false)} disabled={creatingGroup}>
                  Отмена
                </button>
                <button className="btn btn-primary" onClick={() => void createChatGroup()} disabled={creatingGroup || !groupName.trim() || selectedChatsForGroup.length === 0}>
                  {creatingGroup ? 'Создание...' : 'Создать группу'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
