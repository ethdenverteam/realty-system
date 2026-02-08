import { useEffect, useState } from 'react'
import axios from 'axios'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import type {
  AutopublishItem,
  AutopublishListResponse,
  RealtyObjectListItem,
  ApiErrorResponse,
  AutopublishAccountsConfig,
  AutopublishAccountConfig,
  BotChatListItem,
} from '../../types/models'
import './Autopublish.css'

interface TelegramAccount {
  account_id: number
  phone: string
  is_active: boolean
  last_used?: string
  last_error?: string
}

interface ObjectChat {
  chat_id: number
  title: string
  telegram_chat_id: string
  account_id?: number
  account_phone?: string
}

interface ObjectChatsResponse {
  bot_chats: ObjectChat[]
  user_chats: ObjectChat[]
}

export default function Autopublish(): JSX.Element {
  const [items, setItems] = useState<AutopublishItem[]>([])
  const [availableObjects, setAvailableObjects] = useState<RealtyObjectListItem[]>([])
  const [accounts, setAccounts] = useState<TelegramAccount[]>([])
  const [accountChats, setAccountChats] = useState<Record<number, BotChatListItem[]>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [editingObjectId, setEditingObjectId] = useState<string | null>(null)
  const [editingConfig, setEditingConfig] = useState<AutopublishAccountsConfig | null>(null)
  const [loadingChatsForAccount, setLoadingChatsForAccount] = useState<number | null>(null)
  const [objectChats, setObjectChats] = useState<Record<string, ObjectChatsResponse>>({})
  const [loadingChatsForObject, setLoadingChatsForObject] = useState<string | null>(null)

  useEffect(() => {
    void loadData()
    void loadAccounts()
  }, [])

  const loadData = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<AutopublishListResponse>('/user/dashboard/autopublish')
      setItems(res.data.autopublish_items || [])
      setAvailableObjects(res.data.available_objects || [])
    } catch (err: unknown) {
      setError('Ошибка загрузки настроек автопубликации')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setLoading(false)
    }
  }

  const loadAccounts = async (): Promise<void> => {
    try {
      const res = await api.get<TelegramAccount[]>('/accounts')
      // Берём только активные аккаунты пользователя
      setAccounts(res.data.filter((a) => a.is_active))
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error('Error loading accounts:', err.response?.data || err.message)
      } else {
        console.error('Error loading accounts:', err)
      }
    }
  }

  const loadChatsForAccount = async (accountId: number): Promise<void> => {
    try {
      setLoadingChatsForAccount(accountId)
      const res = await api.get<BotChatListItem[]>('/chats', {
        params: { owner_type: 'user', account_id: accountId },
      })
      setAccountChats((prev) => ({ ...prev, [accountId]: res.data }))
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error('Error loading chats:', err.response?.data || err.message)
      } else {
        console.error('Error loading chats:', err)
      }
    } finally {
      setLoadingChatsForAccount(null)
    }
  }

  const handleAddObject = async (objectId: string): Promise<void> => {
    try {
      setSaving(true)
      setError('')
      const res = await api.post<{ success: boolean }>('/user/dashboard/autopublish', {
        object_id: objectId,
        bot_enabled: true,
      })
      if (res.data.success) {
        setSuccess('Объект добавлен в автопубликацию')
        setTimeout(() => setSuccess(''), 3000)
        await loadData()
      }
    } catch (err: unknown) {
      setError('Ошибка добавления объекта на автопубликацию')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setSaving(false)
    }
  }

  const handleToggleEnabled = async (objectId: string, enabled: boolean): Promise<void> => {
    try {
      setSaving(true)
      setError('')
      const res = await api.put<{ success: boolean }>(`/user/dashboard/autopublish/${objectId}`, {
        enabled: !enabled,
      })
      if (res.data.success) {
        await loadData()
      }
    } catch (err: unknown) {
      setError('Ошибка изменения настройки автопубликации')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setSaving(false)
    }
  }
  const openAccountsModal = (item: AutopublishItem): void => {
    const baseConfig: AutopublishAccountsConfig = item.config.accounts_config_json || { accounts: [] }
    setEditingObjectId(item.object.object_id as string)
    setEditingConfig({
      accounts: baseConfig.accounts.map((a) => ({
        account_id: a.account_id,
        chat_ids: [...a.chat_ids],
      })),
    })
  }

  const closeAccountsModal = (): void => {
    setEditingObjectId(null)
    setEditingConfig(null)
  }

  const toggleAccountForEditing = (accountId: number): void => {
    if (!editingConfig) return
    const exists = editingConfig.accounts.find((a) => a.account_id === accountId)
    let nextAccounts: AutopublishAccountConfig[]
    if (exists) {
      nextAccounts = editingConfig.accounts.filter((a) => a.account_id !== accountId)
    } else {
      nextAccounts = [...editingConfig.accounts, { account_id: accountId, chat_ids: [] }]
      if (!accountChats[accountId]) {
        void loadChatsForAccount(accountId)
      }
    }
    setEditingConfig({ accounts: nextAccounts })
  }

  const toggleChatForEditing = (accountId: number, chatId: number | string): void => {
    if (!editingConfig) return
    const accountsCopy = editingConfig.accounts.map((a) => ({ ...a, chat_ids: [...a.chat_ids] }))
    const acc = accountsCopy.find((a) => a.account_id === accountId)
    if (!acc) return
    const idStr = String(chatId)
    const has = acc.chat_ids.map(String).includes(idStr)
    acc.chat_ids = has
      ? acc.chat_ids.filter((cid) => String(cid) !== idStr)
      : [...acc.chat_ids, chatId]
    setEditingConfig({ accounts: accountsCopy })
  }

  const saveAccountsConfig = async (): Promise<void> => {
    if (!editingObjectId || !editingConfig) return
    
    // Проверяем, что есть хотя бы один аккаунт с выбранными чатами
    const hasValidAccounts = editingConfig.accounts.some(acc => acc.chat_ids && acc.chat_ids.length > 0)
    if (!hasValidAccounts) {
      setError('Сначала выберите чаты для аккаунтов')
      return
    }
    
    try {
      setSaving(true)
      setError('')
      const res = await api.put<{ success: boolean }>(`/user/dashboard/autopublish/${editingObjectId}`, {
        accounts_config_json: editingConfig,
      })
      if (res.data.success) {
        setSuccess('Настройки аккаунтов для автопубликации сохранены')
        setTimeout(() => setSuccess(''), 3000)
        closeAccountsModal()
        await loadData()
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        const errorMsg = err.response?.data?.error || 'Ошибка сохранения настроек аккаунтов'
        setError(errorMsg)
        if (errorMsg.includes('Сначала выберите чаты')) {
          setError('Сначала выберите чаты для аккаунтов. Нельзя включить автопубликацию через аккаунты без выбранных чатов.')
        }
      } else {
        setError('Ошибка сохранения настроек аккаунтов')
      }
    } finally {
      setSaving(false)
    }
  }


  const handleDelete = async (objectId: string): Promise<void> => {
    const confirmed = window.confirm('Убрать объект из автопубликации?')
    if (!confirmed) return

    try {
      setSaving(true)
      setError('')
      const res = await api.delete<{ success: boolean }>(`/user/dashboard/autopublish/${objectId}`)
      if (res.data.success) {
        setSuccess('Объект удален из автопубликации')
        setTimeout(() => setSuccess(''), 3000)
        await loadData()
      }
    } catch (err: unknown) {
      setError('Ошибка удаления объекта из автопубликации')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setSaving(false)
    }
  }

  const loadChatsForObject = async (objectId: string): Promise<void> => {
    try {
      setLoadingChatsForObject(objectId)
      const res = await api.get<ObjectChatsResponse>(`/user/dashboard/autopublish/${objectId}/chats`)
      setObjectChats((prev) => ({ ...prev, [objectId]: res.data }))
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error('Error loading chats:', err.response?.data || err.message)
      } else {
        console.error('Error loading chats:', err)
      }
    } finally {
      setLoadingChatsForObject(null)
    }
  }

  // Удалена функция handleToggleBotEnabled - бот всегда включен

  return (
    <Layout title="Автопубликация">
      <div className="autopublish-page">
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

        <GlassCard className="autopublish-card">
          <div className="autopublish-header">
            <h2 className="card-title">Объекты на автопубликации</h2>
          </div>

          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : items.length === 0 ? (
            <div className="empty-state">
              <p>Нет объектов на автопубликации.</p>
            </div>
          ) : (
            <div className="autopublish-list">
              {items.map((item) => {
                const obj = item.object
                const cfg = item.config
                const accCfg = cfg.accounts_config_json
                const totalAccounts = accCfg?.accounts?.length ?? 0
                const totalChats =
                  accCfg?.accounts?.reduce((sum, a) => sum + (a.chat_ids?.length ?? 0), 0) ?? 0
                return (
                  <div key={obj.object_id} className="object-card compact autopublish-item">
                    <div className="object-details-compact single-line">
                      <span className="object-detail-item">{obj.object_id}</span>
                      {obj.rooms_type && <span className="object-detail-item">{obj.rooms_type}</span>}
                      {obj.price > 0 && <span className="object-detail-item">{obj.price}тр</span>}
                      {(obj.districts_json?.length || 0) > 0 && (
                        <span className="object-detail-item">
                          {(obj.districts_json || []).join(',')}
                        </span>
                      )}
                    </div>
                    <div className="autopublish-flags">
                      <span className="badge badge-success">
                        Включено
                      </span>
                      <span className="badge badge-primary">
                        Бот: всегда включен
                      </span>
                      {totalAccounts > 0 && totalChats > 0 ? (
                        <span className="badge badge-success">
                          Аккаунты: {totalAccounts}, чатов: {totalChats}
                        </span>
                      ) : (
                        <span className="badge badge-secondary">
                          Аккаунты: не выбраны
                        </span>
                      )}
                    </div>
                    <div className="autopublish-actions">
                      <button
                        className="btn btn-small btn-secondary"
                        onClick={() => void handleToggleEnabled(obj.object_id as string, cfg.enabled)}
                        disabled={saving}
                      >
                        {cfg.enabled ? 'Выключить' : 'Включить'}
                      </button>
                      <button
                        className="btn btn-small btn-danger"
                        onClick={() => void handleDelete(obj.object_id as string)}
                        disabled={saving}
                      >
                        Убрать
                      </button>
                      <button
                        className="btn btn-small btn-primary"
                        type="button"
                        onClick={() => openAccountsModal(item)}
                      >
                        Аккаунты и чаты
                      </button>
                      <button
                        className="btn btn-small btn-secondary"
                        type="button"
                        onClick={() => {
                          if (!objectChats[obj.object_id as string]) {
                            void loadChatsForObject(obj.object_id as string)
                          }
                        }}
                        disabled={loadingChatsForObject === obj.object_id}
                      >
                        {loadingChatsForObject === obj.object_id ? 'Загрузка...' : 'Список чатов'}
                      </button>
                    </div>
                    {objectChats[obj.object_id as string] && (
                      <div className="autopublish-chats-preview">
                        <div className="chats-preview-section">
                          <strong>Админские чаты (бот):</strong>
                          {objectChats[obj.object_id as string].bot_chats.length > 0 ? (
                            <ul className="chats-list">
                              {objectChats[obj.object_id as string].bot_chats.map((chat) => (
                                <li key={chat.chat_id}>{chat.title}</li>
                              ))}
                            </ul>
                          ) : (
                            <div className="text-muted">Нет подходящих чатов</div>
                          )}
                        </div>
                        <div className="chats-preview-section">
                          <strong>Пользовательские чаты:</strong>
                          {objectChats[obj.object_id as string].user_chats.length > 0 ? (
                            <ul className="chats-list">
                              {objectChats[obj.object_id as string].user_chats.map((chat) => (
                                <li key={chat.chat_id}>
                                  {chat.title} {chat.account_phone && `(${chat.account_phone})`}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div className="text-muted">Нет выбранных чатов</div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </GlassCard>

        <GlassCard className="autopublish-card">
          <h2 className="card-title">Добавить объект на автопубликацию</h2>
          {availableObjects.length === 0 ? (
            <div className="empty-state">
              <p>Нет доступных объектов (кроме архива), которые не в автопубликации.</p>
            </div>
          ) : (
            <div className="autopublish-available-list">
              {availableObjects.map((obj) => (
                <button
                  key={obj.object_id}
                  type="button"
                  className="object-card compact autopublish-available-item"
                  onClick={() => void handleAddObject(obj.object_id as string)}
                  disabled={saving}
                >
                  <div className="object-details-compact single-line">
                    <span className="object-detail-item">{obj.object_id}</span>
                    {obj.rooms_type && <span className="object-detail-item">{obj.rooms_type}</span>}
                    {obj.price > 0 && <span className="object-detail-item">{obj.price}тр</span>}
                    {(obj.districts_json?.length || 0) > 0 && (
                      <span className="object-detail-item">
                        {(obj.districts_json || []).join(',')}
                      </span>
                    )}
                  </div>
                  <span className="badge badge-primary">Добавить</span>
                </button>
              ))}
            </div>
          )}
        </GlassCard>

        {editingObjectId && editingConfig && (
          <div className="modal-overlay" onClick={closeAccountsModal}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Настройки аккаунтов и чатов для автопубликации</h3>
                <button className="modal-close" onClick={closeAccountsModal}>
                  ×
                </button>
              </div>
              <div className="modal-body">
                {accounts.length === 0 ? (
                  <p>Нет активных Telegram-аккаунтов.</p>
                ) : (
                  <div className="autopublish-accounts-list">
                    {accounts.map((acc) => {
                      const isSelected = editingConfig.accounts.some((a) => a.account_id === acc.account_id)
                      const chats = accountChats[acc.account_id] || []
                      const selectedAccountCfg =
                        editingConfig.accounts.find((a) => a.account_id === acc.account_id) || null
                      return (
                        <div key={acc.account_id} className="autopublish-account-block">
                          <label className="autopublish-account-header">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleAccountForEditing(acc.account_id)}
                            />
                            <span>{acc.phone}</span>
                          </label>
                          {isSelected && (
                            <div className="autopublish-account-chats">
                              {loadingChatsForAccount === acc.account_id && (
                                <div className="loading">Загрузка чатов...</div>
                              )}
                              {!loadingChatsForAccount && chats.length === 0 && (
                                <button
                                  type="button"
                                  className="btn btn-small btn-secondary"
                                  onClick={() => void loadChatsForAccount(acc.account_id)}
                                >
                                  Загрузить чаты
                                </button>
                              )}
                              {!loadingChatsForAccount && chats.length > 0 && (
                                <div className="autopublish-chats-list">
                                  {chats.map((chat) => {
                                    const checked =
                                      !!selectedAccountCfg &&
                                      selectedAccountCfg.chat_ids
                                        .map(String)
                                        .includes(String(chat.chat_id))
                                    return (
                                      <label
                                        key={chat.chat_id}
                                        className="autopublish-chat-item"
                                      >
                                        <input
                                          type="checkbox"
                                          checked={checked}
                                          onChange={() =>
                                            toggleChatForEditing(
                                              acc.account_id,
                                              chat.chat_id,
                                            )
                                          }
                                        />
                                        <span>{chat.title}</span>
                                      </label>
                                    )
                                  })}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
              <div className="modal-actions">
                <button className="btn btn-secondary" onClick={closeAccountsModal} disabled={saving}>
                  Отмена
                </button>
                <button className="btn btn-primary" onClick={() => void saveAccountsConfig()} disabled={saving}>
                  {saving ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

