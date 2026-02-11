import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { FilterSelect } from '../../components/FilterSelect'
import { useApiData } from '../../hooks/useApiData'
import { useApiMutation } from '../../hooks/useApiMutation'
import { getErrorMessage, logError } from '../../utils/errorHandler'
import api from '../../utils/api'
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
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [testMessageChatId, setTestMessageChatId] = useState<number | null>(null)
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [showCreateGroupModal, setShowCreateGroupModal] = useState(false)
  const [selectedChatsForGroup, setSelectedChatsForGroup] = useState<number[]>([])
  const [groupName, setGroupName] = useState('')
  const [groupDescription, setGroupDescription] = useState('')

  // Загрузка аккаунтов
  const { data: accountsData, loading: loadingAccounts } = useApiData<TelegramAccount[]>({
    url: '/accounts',
    errorContext: 'Loading accounts',
    defaultErrorMessage: 'Ошибка загрузки аккаунтов',
  })
  const accounts = (accountsData || []).filter(acc => acc.is_active)

  // Автоматический выбор первого аккаунта
  useEffect(() => {
    if (accounts.length > 0 && !selectedAccountId) {
      setSelectedAccountId(accounts[0].account_id)
    }
  }, [accounts, selectedAccountId])

  // Загрузка чатов
  const { data: chatsData, loading: loadingChats, reload: reloadChats } = useApiData<CachedChat[]>({
    url: '/chats',
    params: {
      account_id: selectedAccountId || 0,
      owner_type: 'user',
      ...(search.trim() && { search: search.trim() }),
    },
    deps: [selectedAccountId, search],
    errorContext: 'Loading chats',
    defaultErrorMessage: 'Ошибка загрузки чатов',
    autoLoad: !!selectedAccountId,
  })
  const chats = chatsData || []

  // Обновление чатов (используем прямой вызов API, так как это GET запрос)
  const [refreshing, setRefreshing] = useState(false)
  const refreshChats = async (): Promise<void> => {
    if (!selectedAccountId) return
    try {
      setRefreshing(true)
      setError('')
      const res = await api.get<{ success: boolean; chats: CachedChat[] }>(`/accounts/${selectedAccountId}/chats`)
      if (res.data.success) {
        setSuccess('Чаты обновлены')
        setTimeout(() => setSuccess(''), 3000)
        void reloadChats()
      }
    } catch (err: unknown) {
      const message = getErrorMessage(err, 'Ошибка обновления чатов')
      setError(message)
      logError(err, 'Refreshing chats')
    } finally {
      setRefreshing(false)
    }
  }

  // Отправка тестового сообщения
  const { mutate: sendTestMessage, loading: sendingTest } = useApiMutation<{ chat_id: string; message: string }, { success: boolean; message_id?: number }>({
    url: selectedAccountId ? `/accounts/${selectedAccountId}/test-message` : '',
    method: 'POST',
    errorContext: 'Sending test message',
    defaultErrorMessage: 'Ошибка отправки тестового сообщения',
    onSuccess: () => {
      setSuccess('Тестовое сообщение отправлено')
      setTimeout(() => setSuccess(''), 3000)
      setTestMessageChatId(null)
    },
  })

  // Загрузка объектов для публикации
  const { data: objectsData } = useApiData<{ objects: RealtyObject[] }>({
    url: '/objects',
    errorContext: 'Loading objects',
    defaultErrorMessage: 'Ошибка загрузки объектов',
    autoLoad: false,
  })
  const objects = (objectsData?.objects || []).filter(obj => obj.status !== 'архив')

  const openPublishModal = (chatId: number): void => {
    setSelectedChatId(chatId)
    setShowPublishModal(true)
  }

  // Публикация объекта
  const { mutate: publishObject, loading: publishing } = useApiMutation<{ object_id: string; account_id: number; chat_id: number }, { success: boolean; message_id?: number }>({
    url: '/objects/publish-via-account',
    method: 'POST',
    errorContext: 'Publishing object',
    defaultErrorMessage: 'Ошибка публикации объекта',
    onSuccess: () => {
      setSuccess('Объект успешно опубликован')
      setTimeout(() => {
        setSuccess('')
        setShowPublishModal(false)
        setSelectedChatId(null)
      }, 3000)
    },
  })

  const openCreateGroupModal = (): void => {
    setSelectedChatsForGroup([])
    setGroupName('')
    setGroupDescription('')
    setShowCreateGroupModal(true)
  }

  // Создание группы чатов
  const { mutate: createChatGroup, loading: creatingGroup } = useApiMutation<{ name: string; description?: string; chat_ids: number[] }, { success: boolean; group: ChatGroup }>({
    url: '/chats/groups',
    method: 'POST',
    errorContext: 'Creating chat group',
    defaultErrorMessage: 'Ошибка создания группы',
    onSuccess: () => {
      setSuccess('Группа чатов создана')
      setTimeout(() => {
        setSuccess('')
        setShowCreateGroupModal(false)
        setSelectedChatsForGroup([])
        setGroupName('')
        setGroupDescription('')
      }, 3000)
    },
    onError: (errorMsg) => {
      setError(errorMsg)
    },
  })

  const handleCreateGroup = (): void => {
    if (!groupName.trim()) {
      setError('Введите название группы')
      return
    }
    if (selectedChatsForGroup.length === 0) {
      setError('Выберите хотя бы один чат')
      return
    }
    void createChatGroup({
      name: groupName.trim(),
      description: groupDescription.trim() || undefined,
      chat_ids: selectedChatsForGroup,
    })
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
                <FilterSelect
                  value={selectedAccountId?.toString() || ''}
                  onChange={(value) => setSelectedAccountId(value ? Number(value) : null)}
                  options={accounts.map(acc => ({ value: acc.account_id.toString(), label: acc.phone }))}
                  placeholder="Выберите аккаунт"
                  size="sm"
                />
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

          {(loadingAccounts || loadingChats) && <div className="loading">Загрузка...</div>}

          {!loadingAccounts && !loadingChats && selectedAccountId && chats.length === 0 && (
            <div className="empty-state">
              <p>Чаты не найдены. Нажмите "Обновить чаты" для загрузки или измените параметры поиска.</p>
            </div>
          )}

          {!loadingAccounts && !loadingChats && chats.length > 0 && (
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
                        if (!selectedAccountId) return
                        setTestMessageChatId(chat.chat_id)
                        void sendTestMessage({
                          chat_id: chat.telegram_chat_id.toString(),
                          message: 'Тестовое сообщение',
                        })
                      }}
                      disabled={(sendingTest && testMessageChatId === chat.chat_id) || !selectedAccountId}
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
                          onClick={() => {
                            if (!selectedAccountId || !selectedChatId) return
                            void publishObject({
                              object_id: obj.object_id,
                              account_id: selectedAccountId,
                              chat_id: selectedChatId,
                            })
                          }}
                          disabled={publishing || !selectedAccountId || !selectedChatId}
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
                <button className="btn btn-primary" onClick={handleCreateGroup} disabled={creatingGroup || !groupName.trim() || selectedChatsForGroup.length === 0}>
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
