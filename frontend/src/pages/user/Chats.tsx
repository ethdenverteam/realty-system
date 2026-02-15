import { useState, useEffect, useMemo } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { FilterSelect } from '../../components/FilterSelect'
import { useApiData } from '../../hooks/useApiData'
import { useApiMutation } from '../../hooks/useApiMutation'
import { getErrorMessage, logError } from '../../utils/errorHandler'
import api from '../../utils/api'
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
  category?: string
  filters_json?: {
    rooms_types?: string[]
    districts?: string[]
    price_min?: number
    price_max?: number
  }
}

interface ChatGroup {
  group_id: number
  name: string
  description?: string
  chat_ids: number[]
  category?: string
  filters_json?: {
    rooms_types?: string[]
    districts?: string[]
    price_min?: number
    price_max?: number
  }
}

export default function Chats(): JSX.Element {
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [search, setSearch] = useState('')
  const [showCreateGroupModal, setShowCreateGroupModal] = useState(false)
  const [showEditGroupModal, setShowEditGroupModal] = useState(false)
  const [editingGroup, setEditingGroup] = useState<ChatGroup | null>(null)
  const [selectedChatsForGroup, setSelectedChatsForGroup] = useState<number[]>([])
  const [selectedChatsForCreate, setSelectedChatsForCreate] = useState<Set<number>>(new Set())
  const [groupName, setGroupName] = useState('')
  const [groupDescription, setGroupDescription] = useState('')
  const [groupCategory, setGroupCategory] = useState('')
  const [groupFilterType, setGroupFilterType] = useState<'' | 'common' | 'rooms' | 'district' | 'price'>('')
  const [groupRoomsTypes, setGroupRoomsTypes] = useState<string[]>([])
  const [groupDistricts, setGroupDistricts] = useState<string[]>([])
  const [groupPriceMin, setGroupPriceMin] = useState('')
  const [groupPriceMax, setGroupPriceMax] = useState('')
  const [groupConfig, setGroupConfig] = useState<{ districts?: Record<string, unknown>; rooms_types?: string[]; price_ranges?: Array<{ min: number; max: number; label: string }> } | null>(null)
  const [showChatCategoryModal, setShowChatCategoryModal] = useState(false)
  const [editingChat, setEditingChat] = useState<CachedChat | null>(null)
  const [chatCategory, setChatCategory] = useState('')
  const [chatFilterType, setChatFilterType] = useState<'' | 'common' | 'rooms' | 'district' | 'price'>('')
  const [chatRoomsTypes, setChatRoomsTypes] = useState<string[]>([])
  const [chatDistricts, setChatDistricts] = useState<string[]>([])
  const [chatPriceMin, setChatPriceMin] = useState('')
  const [chatPriceMax, setChatPriceMax] = useState('')

  // Загрузка аккаунтов
  const { data: accountsData, loading: loadingAccounts } = useApiData<TelegramAccount[]>({
    url: '/accounts',
    errorContext: 'Loading accounts',
    defaultErrorMessage: 'Ошибка загрузки аккаунтов',
  })
  const accounts = (accountsData || []).filter(acc => acc.is_active)

  // Автоматический выбор первого аккаунта
  useEffect(() => {
    if (accounts.length > 0 && !selectedAccountId && accounts[0]) {
      setSelectedAccountId(accounts[0].account_id)
    }
  }, [accounts, selectedAccountId])

  // Загрузка групп чатов
  const { data: groupsData, loading: loadingGroups, reload: reloadGroups } = useApiData<ChatGroup[]>({
    url: '/chats/groups',
    errorContext: 'Loading chat groups',
    defaultErrorMessage: 'Ошибка загрузки групп чатов',
  })
  const groups = groupsData || []

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

  // Вычисляем группы для каждого чата
  const chatGroupsMap = useMemo(() => {
    const map = new Map<number, ChatGroup[]>()
    chats.forEach(chat => {
      const chatGroups = groups.filter(g => g.chat_ids.includes(chat.chat_id))
      if (chatGroups.length > 0) {
        map.set(chat.chat_id, chatGroups)
      }
    })
    return map
  }, [chats, groups])

  // Обновление чатов
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

  // Загрузка конфигурации для категорий связи
  const loadConfig = async (): Promise<void> => {
    try {
      const res = await api.get<{ districts?: Record<string, unknown>; rooms_types?: string[]; price_ranges?: Array<{ min: number; max: number; label: string }> }>('/admin/dashboard/bot-chats/config')
      setGroupConfig(res.data)
    } catch (err) {
      console.error('Error loading config:', err)
    }
  }

  useEffect(() => {
    if (showCreateGroupModal || showEditGroupModal || showChatCategoryModal) {
      void loadConfig()
    }
  }, [showCreateGroupModal, showEditGroupModal, showChatCategoryModal])

  const openCreateGroupModal = (): void => {
    // Используем выбранные чаты из чекбоксов
    setSelectedChatsForGroup(Array.from(selectedChatsForCreate))
    setGroupName('')
    setGroupDescription('')
    setGroupCategory('')
    setGroupFilterType('')
    setGroupRoomsTypes([])
    setGroupDistricts([])
    setGroupPriceMin('')
    setGroupPriceMax('')
    setShowCreateGroupModal(true)
  }

  const openEditGroupModal = (group: ChatGroup): void => {
    setEditingGroup(group)
    setSelectedChatsForGroup([...group.chat_ids])
    setGroupName(group.name)
    setGroupDescription(group.description || '')
    setGroupCategory(group.category || '')
    
    // Парсим filters_json для редактирования
    if (group.filters_json) {
      if (group.filters_json.rooms_types) {
        setGroupFilterType('rooms')
        setGroupRoomsTypes(group.filters_json.rooms_types || [])
      } else if (group.filters_json.districts) {
        setGroupFilterType('district')
        setGroupDistricts(group.filters_json.districts || [])
      } else if (group.filters_json.price_min !== undefined || group.filters_json.price_max !== undefined) {
        setGroupFilterType('price')
        setGroupPriceMin(group.filters_json.price_min?.toString() || '')
        setGroupPriceMax(group.filters_json.price_max?.toString() || '')
      } else if (group.filters_json.binding_type === 'common') {
        setGroupFilterType('common')
      } else {
        setGroupFilterType('')
      }
    } else if (group.category) {
      // Legacy категория
      if (group.category.startsWith('rooms_')) {
        setGroupFilterType('rooms')
        setGroupRoomsTypes([group.category.replace('rooms_', '')])
      } else if (group.category.startsWith('district_')) {
        setGroupFilterType('district')
        setGroupDistricts([group.category.replace('district_', '')])
      } else if (group.category.startsWith('price_')) {
        setGroupFilterType('price')
        const parts = group.category.replace('price_', '').split('_')
        if (parts.length === 2) {
          setGroupPriceMin(parts[0])
          setGroupPriceMax(parts[1])
        }
      } else {
        setGroupFilterType('')
      }
    } else {
      setGroupFilterType('')
    }
    
    setShowEditGroupModal(true)
  }

  const closeGroupModal = (): void => {
    setShowCreateGroupModal(false)
    setShowEditGroupModal(false)
    setEditingGroup(null)
    setSelectedChatsForGroup([])
    setGroupName('')
    setGroupDescription('')
    setGroupCategory('')
    setGroupFilterType('')
    setGroupRoomsTypes([])
    setGroupDistricts([])
    setGroupPriceMin('')
    setGroupPriceMax('')
    // Не очищаем selectedChatsForCreate - они остаются для следующего создания группы
  }

  // Создание группы чатов
  const { mutate: createChatGroup, loading: creatingGroup } = useApiMutation<{ name: string; description?: string; chat_ids: number[]; category?: string; filters_json?: any }, { success: boolean; group: ChatGroup }>({
    url: '/chats/groups',
    method: 'POST',
    errorContext: 'Creating chat group',
    defaultErrorMessage: 'Ошибка создания группы',
    onSuccess: () => {
      setSuccess('Группа чатов создана')
      setTimeout(() => setSuccess(''), 3000)
      closeGroupModal()
      void reloadGroups()
    },
    onError: (errorMsg) => {
      setError(errorMsg)
    },
  })

  // Обновление группы чатов
  const { mutate: updateChatGroup, loading: updatingGroup } = useApiMutation<{ name: string; description?: string; chat_ids: number[]; category?: string; filters_json?: any }, { success: boolean; group: ChatGroup }>({
    url: editingGroup ? `/chats/groups/${editingGroup.group_id}` : '',
    method: 'PUT',
    errorContext: 'Updating chat group',
    defaultErrorMessage: 'Ошибка обновления группы',
    onSuccess: () => {
      setSuccess('Группа чатов обновлена')
      setTimeout(() => setSuccess(''), 3000)
      closeGroupModal()
      void reloadGroups()
    },
    onError: (errorMsg) => {
      setError(errorMsg)
    },
  })

  const handleSaveGroup = (): void => {
    if (!groupName.trim()) {
      setError('Введите название группы')
      return
    }
    if (selectedChatsForGroup.length === 0) {
      setError('Выберите хотя бы один чат')
      return
    }
    
    // Формируем filters_json на основе выбранного типа
    let filtersJson: any = null
    let category: string | undefined = undefined
    
    if (groupFilterType === 'common') {
      filtersJson = { binding_type: 'common' }
    } else if (groupFilterType === 'rooms' && groupRoomsTypes.length > 0) {
      filtersJson = { rooms_types: groupRoomsTypes }
      // Legacy категория для обратной совместимости
      if (groupRoomsTypes.length === 1) {
        category = `rooms_${groupRoomsTypes[0]}`
      }
    } else if (groupFilterType === 'district' && groupDistricts.length > 0) {
      filtersJson = { districts: groupDistricts }
      // Legacy категория для обратной совместимости
      if (groupDistricts.length === 1) {
        category = `district_${groupDistricts[0]}`
      }
    } else if (groupFilterType === 'price' && (groupPriceMin || groupPriceMax)) {
      filtersJson = {
        price_min: groupPriceMin ? parseFloat(groupPriceMin) : null,
        price_max: groupPriceMax ? parseFloat(groupPriceMax) : null,
      }
      // Legacy категория для обратной совместимости
      if (groupPriceMin && groupPriceMax) {
        category = `price_${groupPriceMin}_${groupPriceMax}`
      }
    }
    
    const groupData = {
      name: groupName.trim(),
      description: groupDescription.trim() || undefined,
      chat_ids: selectedChatsForGroup,
      category: category,
      filters_json: filtersJson,
    }
    if (editingGroup) {
      void updateChatGroup(groupData)
    } else {
      void createChatGroup(groupData)
    }
  }

  // Открытие модального окна для установки категории чата
  const openChatCategoryModal = (chat: CachedChat): void => {
    setEditingChat(chat)
    setChatCategory(chat.category || '')
    
    // Парсим filters_json для редактирования
    if (chat.filters_json) {
      if (chat.filters_json.rooms_types) {
        setChatFilterType('rooms')
        setChatRoomsTypes(chat.filters_json.rooms_types || [])
      } else if (chat.filters_json.districts) {
        setChatFilterType('district')
        setChatDistricts(chat.filters_json.districts || [])
      } else if (chat.filters_json.price_min !== undefined || chat.filters_json.price_max !== undefined) {
        setChatFilterType('price')
        setChatPriceMin(chat.filters_json.price_min?.toString() || '')
        setChatPriceMax(chat.filters_json.price_max?.toString() || '')
      } else if (chat.filters_json.binding_type === 'common') {
        setChatFilterType('common')
      } else {
        setChatFilterType('')
      }
    } else if (chat.category) {
      // Legacy категория
      if (chat.category.startsWith('rooms_')) {
        setChatFilterType('rooms')
        setChatRoomsTypes([chat.category.replace('rooms_', '')])
      } else if (chat.category.startsWith('district_')) {
        setChatFilterType('district')
        setChatDistricts([chat.category.replace('district_', '')])
      } else if (chat.category.startsWith('price_')) {
        setChatFilterType('price')
        const parts = chat.category.replace('price_', '').split('_')
        if (parts.length === 2) {
          setChatPriceMin(parts[0])
          setChatPriceMax(parts[1])
        }
      } else {
        setChatFilterType('')
      }
    } else {
      setChatFilterType('')
    }
    setShowChatCategoryModal(true)
  }

  // Обновление категории чата
  const { mutate: updateChatCategory, loading: updatingChatCategory } = useApiMutation<{ category?: string }, { success: boolean }>({
    url: editingChat ? `/chats/${editingChat.chat_id}` : '',
    method: 'PUT',
    errorContext: 'Updating chat category',
    defaultErrorMessage: 'Ошибка обновления категории чата',
    onSuccess: () => {
      setSuccess('Категория чата обновлена')
      setTimeout(() => setSuccess(''), 3000)
      setShowChatCategoryModal(false)
      setEditingChat(null)
      setChatCategory('')
      void reloadChats()
    },
    onError: (errorMsg) => {
      setError(errorMsg)
    },
  })

  const handleSaveChatCategory = (): void => {
    if (!editingChat) return
    
    // Формируем filters_json на основе выбранного типа
    let filtersJson: any = null
    let category: string | undefined = undefined
    
    if (chatFilterType === 'common') {
      filtersJson = { binding_type: 'common' }
    } else if (chatFilterType === 'rooms' && chatRoomsTypes.length > 0) {
      filtersJson = { rooms_types: chatRoomsTypes }
      // Legacy категория для обратной совместимости
      if (chatRoomsTypes.length === 1) {
        category = `rooms_${chatRoomsTypes[0]}`
      }
    } else if (chatFilterType === 'district' && chatDistricts.length > 0) {
      filtersJson = { districts: chatDistricts }
      // Legacy категория для обратной совместимости
      if (chatDistricts.length === 1) {
        category = `district_${chatDistricts[0]}`
      }
    } else if (chatFilterType === 'price' && (chatPriceMin || chatPriceMax)) {
      filtersJson = {
        price_min: chatPriceMin ? parseFloat(chatPriceMin) : null,
        price_max: chatPriceMax ? parseFloat(chatPriceMax) : null,
      }
      // Legacy категория для обратной совместимости
      if (chatPriceMin && chatPriceMax) {
        category = `price_${chatPriceMin}_${chatPriceMax}`
      }
    }
    
    void updateChatCategory({
      category: category,
      filters_json: filtersJson,
    })
  }

  // Форматирование категории для отображения
  const formatCategory = (category?: string): string => {
    if (!category) return 'Без категории'
    if (category.startsWith('rooms_')) {
      return `Комнаты: ${category.replace('rooms_', '')}`
    }
    if (category.startsWith('district_')) {
      return `Район: ${category.replace('district_', '')}`
    }
    if (category.startsWith('price_')) {
      const parts = category.replace('price_', '').split('_')
      if (parts.length === 2) {
        return `Цена: ${parts[0]}-${parts[1]} тыс.`
      }
    }
    return category
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

        {/* Список групп чатов */}
        {groups.length > 0 && (
          <GlassCard className="chats-card">
            <div className="card-header-row">
              <h2 className="card-title">Группы чатов</h2>
            </div>
            <div className="chat-groups-list">
              {groups.map(group => {
                const groupChats = chats.filter(c => group.chat_ids.includes(c.chat_id))
                return (
                  <div key={group.group_id} className="chat-group-item">
                    <div className="chat-group-header">
                      <div className="chat-group-info">
                        <h3 className="chat-group-name">{group.name}</h3>
                        {group.description && (
                          <p className="chat-group-description">{group.description}</p>
                        )}
                        <div className="chat-group-details">
                          <span className="chat-group-chats-count">
                            Чатов: {groupChats.length}
                          </span>
                          {group.category && (
                            <span className="chat-group-category">
                              Категория: {formatCategory(group.category)}
                            </span>
                          )}
                        </div>
                        {groupChats.length > 0 && (
                          <div className="chat-group-chats">
                            {groupChats.map(chat => (
                              <span key={chat.chat_id} className="chat-group-chat-name">
                                {chat.title}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <button
                        className="btn btn-small btn-secondary"
                        onClick={() => openEditGroupModal(group)}
                      >
                        Изменить
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </GlassCard>
        )}

        <GlassCard className="chats-card">
          <div className="card-header-row">
            <h2 className="card-title">
              Чаты из аккаунтов
              {selectedAccountId && !loadingChats && (
                <span className="chats-count"> ({chats.length})</span>
              )}
            </h2>
          </div>
          <div className="chats-controls">
            <div className="chats-control-row chats-control-row-1">
              <FilterSelect
                value={selectedAccountId?.toString() || ''}
                onChange={(value) => setSelectedAccountId(value ? Number(value) : null)}
                options={accounts.map(acc => ({ value: acc.account_id.toString(), label: acc.phone }))}
                placeholder="Выберите аккаунт"
                size="sm"
              />
            </div>
            {selectedAccountId && (
              <>
                <div className="chats-control-row chats-control-row-2">
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
                    disabled={chats.length === 0 || selectedChatsForCreate.size === 0}
                    title={selectedChatsForCreate.size === 0 ? 'Выберите хотя бы один чат' : ''}
                  >
                    Создать группу {selectedChatsForCreate.size > 0 && `(${selectedChatsForCreate.size})`}
                  </button>
                </div>
                <div className="chats-control-row chats-control-row-3">
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
              </>
            )}
          </div>

          {loadingAccounts ? (
            <div className="loading">Загрузка аккаунтов...</div>
          ) : accounts.length === 0 ? (
            <div className="empty-state">
              <p>Нет активных аккаунтов. Подключите аккаунт в настройках Telegram аккаунтов.</p>
            </div>
          ) : !selectedAccountId ? (
            <div className="empty-state">
              <p>Выберите аккаунт для просмотра чатов.</p>
            </div>
          ) : loadingChats ? (
            <div className="loading">Загрузка чатов...</div>
          ) : chats.length === 0 ? (
            <div className="empty-state">
              <p>Чаты не найдены. Нажмите "Обновить чаты" для загрузки или измените параметры поиска.</p>
            </div>
          ) : (
            <div className="objects-list chats-list">
              {chats.map(chat => {
                const chatGroups = chatGroupsMap.get(chat.chat_id) || []
                const isSelected = selectedChatsForCreate.has(chat.chat_id)
                return (
                  <div key={chat.chat_id} className={`object-card compact chat-item ${isSelected ? 'selected' : ''}`}>
                    <div className="chat-item-content">
                      <div className="chat-item-main">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              const newSelected = new Set(selectedChatsForCreate)
                              if (e.target.checked) {
                                newSelected.add(chat.chat_id)
                              } else {
                                newSelected.delete(chat.chat_id)
                              }
                              setSelectedChatsForCreate(newSelected)
                            }}
                            onClick={(e) => e.stopPropagation()}
                            style={{ cursor: 'pointer' }}
                          />
                          <h3 className="chat-item-title">{chat.title}</h3>
                        </div>
                        <div className="chat-item-meta">
                          {chatGroups.length > 0 && (
                            <div className="chat-item-groups">
                              <span className="chat-item-groups-label">Группы:</span>
                              {chatGroups.map((group, idx) => (
                                <span key={group.group_id} className="chat-item-group-tag">
                                  {group.name}
                                  {group.category && ` (${formatCategory(group.category)})`}
                                  {idx < chatGroups.length - 1 && ', '}
                                </span>
                              ))}
                            </div>
                          )}
                          {chat.category && (
                            <div className="chat-item-category">
                              <span className="chat-item-category-label">Категория:</span>
                              <span className="chat-item-category-value">{formatCategory(chat.category)}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      <button
                        className="btn btn-small btn-secondary"
                        onClick={() => openChatCategoryModal(chat)}
                      >
                        Установить категорию
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </GlassCard>

        {/* Модальное окно создания/редактирования группы */}
        {(showCreateGroupModal || showEditGroupModal) && (
          <div className="modal-overlay" onClick={closeGroupModal}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>{editingGroup ? 'Изменить группу чатов' : 'Создать группу чатов'}</h3>
                <button className="modal-close" onClick={closeGroupModal}>×</button>
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
                  <label className="form-label">Тип категории связи</label>
                  <select
                    className="form-control"
                    value={groupFilterType}
                    onChange={(e) => {
                      const newType = e.target.value as '' | 'common' | 'rooms' | 'district' | 'price'
                      setGroupFilterType(newType)
                      // Сброс значений при смене типа
                      setGroupRoomsTypes([])
                      setGroupDistricts([])
                      setGroupPriceMin('')
                      setGroupPriceMax('')
                    }}
                  >
                    <option value="">Без привязки</option>
                    <option value="common">Общий (все посты)</option>
                    <option value="rooms">По типу комнат</option>
                    <option value="district">По району</option>
                    <option value="price">По диапазону цен</option>
                  </select>
                </div>

                {groupFilterType === 'rooms' && groupConfig && (
                  <div className="form-group">
                    <label className="form-label">Типы комнат</label>
                    <div className="checkbox-group">
                      {(groupConfig.rooms_types || []).map((rt) => (
                        <label key={rt} className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={groupRoomsTypes.includes(rt)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setGroupRoomsTypes([...groupRoomsTypes, rt])
                              } else {
                                setGroupRoomsTypes(groupRoomsTypes.filter((x) => x !== rt))
                              }
                            }}
                          />
                          <span>{rt}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {groupFilterType === 'district' && groupConfig && (
                  <div className="form-group">
                    <label className="form-label">Районы</label>
                    <select
                      className="form-control"
                      multiple
                      value={groupDistricts}
                      onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                        const selected = Array.from(e.target.selectedOptions).map((opt) => opt.value)
                        setGroupDistricts(selected)
                      }}
                    >
                      {Object.keys(groupConfig.districts || {}).map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                    <small className="form-text text-muted">Удерживайте Ctrl для выбора нескольких</small>
                  </div>
                )}

                {groupFilterType === 'price' && (
                  <>
                    <div className="form-group">
                      <label className="form-label">Минимальная цена (тыс. руб.)</label>
                      <input
                        type="number"
                        className="form-control"
                        value={groupPriceMin}
                        onChange={(e) => setGroupPriceMin(e.target.value)}
                        min="0"
                        step="100"
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Максимальная цена (тыс. руб.)</label>
                      <input
                        type="number"
                        className="form-control"
                        value={groupPriceMax}
                        onChange={(e) => setGroupPriceMax(e.target.value)}
                        min="0"
                        step="100"
                      />
                    </div>
                  </>
                )}
                <div className="form-group">
                  <label className="form-label">Выберите чаты для группы ({selectedChatsForGroup.length} выбрано)</label>
                  {chats.length === 0 ? (
                    <p className="text-muted">Нет доступных чатов</p>
                  ) : (
                    <div className="chats-selection-list">
                      {chats.map(chat => (
                        <label key={chat.chat_id} className="chat-selection-item">
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
                          />
                          <span>{chat.title} ({chat.type})</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
                {selectedChatsForGroup.length > 0 && (
                  <div className="form-group">
                    <label className="form-label">Выбранные чаты:</label>
                    <ul className="selected-chats-list">
                      {chats.filter(c => selectedChatsForGroup.includes(c.chat_id)).map(chat => (
                        <li key={chat.chat_id} className="selected-chat-item">
                          <span>{chat.title}</span>
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
                  </div>
                )}
              </div>
              <div className="modal-actions">
                <button className="btn btn-secondary" onClick={closeGroupModal} disabled={creatingGroup || updatingGroup}>
                  Отмена
                </button>
                <button className="btn btn-primary" onClick={handleSaveGroup} disabled={creatingGroup || updatingGroup || !groupName.trim() || selectedChatsForGroup.length === 0 || (groupFilterType && groupFilterType !== 'common' && ((groupFilterType === 'rooms' && groupRoomsTypes.length === 0) || (groupFilterType === 'district' && groupDistricts.length === 0) || (groupFilterType === 'price' && !groupPriceMin && !groupPriceMax)))}>
                  {creatingGroup || updatingGroup ? 'Сохранение...' : (editingGroup ? 'Сохранить' : 'Создать группу')}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Модальное окно установки категории чата */}
        {showChatCategoryModal && editingChat && (
          <div className="modal-overlay" onClick={() => {
            setShowChatCategoryModal(false)
            setEditingChat(null)
            setChatCategory('')
          }}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Установить категорию связи для чата</h3>
                <button className="modal-close" onClick={() => {
                  setShowChatCategoryModal(false)
                  setEditingChat(null)
                  setChatCategory('')
                }}>×</button>
              </div>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Название чата</label>
                  <input
                    type="text"
                    className="form-control"
                    value={editingChat.title}
                    disabled
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Тип категории связи</label>
                  <select
                    className="form-control"
                    value={chatFilterType}
                    onChange={(e) => {
                      const newType = e.target.value as '' | 'common' | 'rooms' | 'district' | 'price'
                      setChatFilterType(newType)
                      // Сброс значений при смене типа
                      setChatRoomsTypes([])
                      setChatDistricts([])
                      setChatPriceMin('')
                      setChatPriceMax('')
                    }}
                  >
                    <option value="">Без привязки</option>
                    <option value="common">Общий (все посты)</option>
                    <option value="rooms">По типу комнат</option>
                    <option value="district">По району</option>
                    <option value="price">По диапазону цен</option>
                  </select>
                </div>

                {chatFilterType === 'rooms' && groupConfig && (
                  <div className="form-group">
                    <label className="form-label">Типы комнат</label>
                    <div className="checkbox-group">
                      {(groupConfig.rooms_types || []).map((rt) => (
                        <label key={rt} className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={chatRoomsTypes.includes(rt)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setChatRoomsTypes([...chatRoomsTypes, rt])
                              } else {
                                setChatRoomsTypes(chatRoomsTypes.filter((x) => x !== rt))
                              }
                            }}
                          />
                          <span>{rt}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {chatFilterType === 'district' && groupConfig && (
                  <div className="form-group">
                    <label className="form-label">Районы</label>
                    <select
                      className="form-control"
                      multiple
                      value={chatDistricts}
                      onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                        const selected = Array.from(e.target.selectedOptions).map((opt) => opt.value)
                        setChatDistricts(selected)
                      }}
                    >
                      {Object.keys(groupConfig.districts || {}).map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                    <small className="form-text text-muted">Удерживайте Ctrl для выбора нескольких</small>
                  </div>
                )}

                {chatFilterType === 'price' && (
                  <>
                    <div className="form-group">
                      <label className="form-label">Минимальная цена (тыс. руб.)</label>
                      <input
                        type="number"
                        className="form-control"
                        value={chatPriceMin}
                        onChange={(e) => setChatPriceMin(e.target.value)}
                        min="0"
                        step="100"
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Максимальная цена (тыс. руб.)</label>
                      <input
                        type="number"
                        className="form-control"
                        value={chatPriceMax}
                        onChange={(e) => setChatPriceMax(e.target.value)}
                        min="0"
                        step="100"
                      />
                    </div>
                  </>
                )}
              </div>
              <div className="modal-actions">
                <button className="btn btn-secondary" onClick={() => {
                  setShowChatCategoryModal(false)
                  setEditingChat(null)
                  setChatCategory('')
                }} disabled={updatingChatCategory}>
                  Отмена
                </button>
                <button className="btn btn-primary" onClick={handleSaveChatCategory} disabled={updatingChatCategory || (chatFilterType && chatFilterType !== 'common' && ((chatFilterType === 'rooms' && chatRoomsTypes.length === 0) || (chatFilterType === 'district' && chatDistricts.length === 0) || (chatFilterType === 'price' && !chatPriceMin && !chatPriceMax)))}>
                  {updatingChatCategory ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
