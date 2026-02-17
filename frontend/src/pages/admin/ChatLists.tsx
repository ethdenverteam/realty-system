import { useState } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { useApiData } from '../../hooks/useApiData'
import { useApiMutation } from '../../hooks/useApiMutation'
import { getErrorMessage, logError } from '../../utils/errorHandler'
import api from '../../utils/api'
import './ChatLists.css'

interface AdminChat {
  chat_id: number
  telegram_chat_id: string
  title: string
  owner_type: string
  account_id?: number | null
  account_phone?: string | null
}

interface AdminChatGroup {
  group_id: number
  user_id: number
  user_name?: string | null
  name: string
  description?: string | null
  purpose: string
  chat_ids: number[]
  chat_links?: string[]
  created_at: string
  updated_at: string
  chats: AdminChat[]
}

export default function AdminChatLists(): JSX.Element {
  const { data: groups, loading, reload } = useApiData<AdminChatGroup[]>({
    url: '/admin/dashboard/chat-lists',
    errorContext: 'Loading admin chat lists',
    defaultErrorMessage: 'Ошибка загрузки списков чатов',
  })

  const [expandedGroupIds, setExpandedGroupIds] = useState<Set<number>>(new Set())
  const [newListUserId, setNewListUserId] = useState('')
  const [newListName, setNewListName] = useState('')
  const [newListLinks, setNewListLinks] = useState('')
  const [addingChatForGroup, setAddingChatForGroup] = useState<number | null>(null)
  const [newChatLink, setNewChatLink] = useState('')

  const toggleExpanded = (groupId: number): void => {
    setExpandedGroupIds((prev) => {
      const next = new Set(prev)
      if (next.has(groupId)) {
        next.delete(groupId)
      } else {
        next.add(groupId)
      }
      return next
    })
  }

  const createListMutation = useApiMutation<AdminChatGroup>({
    url: '/admin/dashboard/chat-lists',
    method: 'POST',
    onSuccess: () => {
      setNewListUserId('')
      setNewListName('')
      setNewListLinks('')
      reload()
    },
  })

  const deleteListMutation = useApiMutation({
    url: '', // будет переопределён перед вызовом
    method: 'DELETE',
    onSuccess: () => {
      reload()
    },
  })

  const addChatMutation = useApiMutation<AdminChatGroup>({
    url: '', // будет переопределён перед вызовом
    method: 'POST',
    onSuccess: () => {
      setAddingChatForGroup(null)
      setNewChatLink('')
      reload()
    },
  })

  const removeChatMutation = useApiMutation<AdminChatGroup>({
    url: '', // будет переопределён перед вызовом
    method: 'DELETE',
    onSuccess: () => {
      reload()
    },
  })

  const handleCreateList = async (): Promise<void> => {
    if (!newListUserId.trim()) {
      alert('Укажите user_id владельца списка')
      return
    }
    if (!newListName.trim()) {
      alert('Введите название списка')
      return
    }
    if (!newListLinks.trim()) {
      alert('Введите ссылки на чаты')
      return
    }

    try {
      await createListMutation.mutate({
        user_id: Number(newListUserId),
        name: newListName.trim(),
        links: newListLinks,
      } as any)
    } catch (error) {
      logError(error, 'Creating admin chat list')
      alert(getErrorMessage(error, 'Ошибка создания списка'))
    }
  }

  const handleDeleteList = async (group: AdminChatGroup): Promise<void> => {
    if (!confirm(`Удалить список "${group.name}" (ID ${group.group_id})?`)) {
      return
    }
    try {
      await deleteListMutation.mutate({}, { url: `/admin/dashboard/chat-lists/${group.group_id}` })
    } catch (error) {
      logError(error, 'Deleting admin chat list')
      alert(getErrorMessage(error, 'Ошибка удаления списка'))
    }
  }

  const handleAddChat = async (group: AdminChatGroup): Promise<void> => {
    if (!newChatLink.trim()) {
      alert('Введите ссылку на чат')
      return
    }
    try {
      await addChatMutation.mutate(
        { link: newChatLink.trim() } as any,
        { url: `/admin/dashboard/chat-lists/${group.group_id}/chats` },
      )
    } catch (error) {
      logError(error, 'Adding chat to list')
      alert(getErrorMessage(error, 'Ошибка добавления чата'))
    }
  }

  const handleRemoveChat = async (group: AdminChatGroup, chat: AdminChat): Promise<void> => {
    if (!confirm(`Удалить чат "${chat.title || chat.telegram_chat_id}" из списка "${group.name}"?`)) {
      return
    }
    try {
      await removeChatMutation.mutate(
        {} as any,
        { url: `/admin/dashboard/chat-lists/${group.group_id}/chats/${chat.chat_id}` },
      )
    } catch (error) {
      logError(error, 'Removing chat from list')
      alert(getErrorMessage(error, 'Ошибка удаления чата из списка'))
    }
  }

  return (
    <Layout title="Админ — Списки чатов (подписки)" isAdmin>
      <div className="admin-chat-lists-page">
        <GlassCard className="chat-lists-create-card">
          <h2>Создать новый список чатов (для подписок)</h2>
          <div className="form-grid">
            <div className="form-group">
              <label>user_id владельца списка</label>
              <input
                type="number"
                value={newListUserId}
                onChange={(e) => setNewListUserId(e.target.value)}
                placeholder="Например: 1"
              />
            </div>
            <div className="form-group">
              <label>Название списка</label>
              <input
                type="text"
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
                placeholder="Например: Подписка аккаунта 1"
              />
            </div>
          </div>
          <div className="form-group">
            <label>Ссылки на чаты (каждая строка — отдельная ссылка t.me)</label>
            <textarea
              value={newListLinks}
              onChange={(e) => setNewListLinks(e.target.value)}
              rows={6}
              placeholder="https://t.me/+example1&#10;https://t.me/example_channel"
            />
          </div>
          <button
            className="btn-primary"
            onClick={() => {
              void handleCreateList()
            }}
            disabled={createListMutation.isLoading}
          >
            {createListMutation.isLoading ? 'Создание...' : 'Создать список'}
          </button>
        </GlassCard>

        <GlassCard className="chat-lists-card">
          <h2>Списки чатов для подписок</h2>
          {loading ? (
            <div>Загрузка...</div>
          ) : groups && groups.length > 0 ? (
            <div className="chat-lists-list">
              {groups.map((group) => {
                const isExpanded = expandedGroupIds.has(group.group_id)
                return (
                  <div key={group.group_id} className="chat-list-item">
                    <div className="chat-list-header" onClick={() => toggleExpanded(group.group_id)}>
                      <div className="chat-list-main">
                        <div className="chat-list-title">
                          <span className="chat-list-name">{group.name}</span>
                          <span className="chat-list-meta">
                            ID {group.group_id} • user_id {group.user_id}
                            {group.user_name ? ` (${group.user_name})` : ''}
                          </span>
                        </div>
                        <div className="chat-list-stats">
                          <span>{group.chat_ids.length} чатов</span>
                          <span>{new Date(group.created_at).toLocaleString('ru-RU')}</span>
                        </div>
                      </div>
                      <div className="chat-list-actions">
                        <button
                          className="btn-danger"
                          onClick={(e) => {
                            e.stopPropagation()
                            void handleDeleteList(group)
                          }}
                          disabled={deleteListMutation.isLoading}
                        >
                          Удалить список
                        </button>
                        <button className="btn-secondary" type="button">
                          {isExpanded ? 'Свернуть' : 'Развернуть'}
                        </button>
                      </div>
                    </div>
                    {isExpanded && (
                      <div className="chat-list-body">
                        <div className="chat-list-chats">
                          {group.chats.length > 0 ? (
                            <table>
                              <thead>
                                <tr>
                                  <th>ID</th>
                                  <th>Название</th>
                                  <th>telegram_chat_id</th>
                                  <th>Аккаунт</th>
                                  <th />
                                </tr>
                              </thead>
                              <tbody>
                                {group.chats.map((chat) => (
                                  <tr key={chat.chat_id}>
                                    <td>{chat.chat_id}</td>
                                    <td>{chat.title || '-'}</td>
                                    <td>{chat.telegram_chat_id}</td>
                                    <td>
                                      {chat.account_phone
                                        ? `${chat.account_phone} (ID ${chat.account_id})`
                                        : chat.owner_type}
                                    </td>
                                    <td>
                                      <button
                                        className="btn-danger small"
                                        onClick={() => {
                                          void handleRemoveChat(group, chat)
                                        }}
                                        disabled={removeChatMutation.isLoading}
                                      >
                                        Удалить
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : (
                            <div>Нет чатов в этом списке</div>
                          )}
                        </div>
                        <div className="chat-list-add-chat">
                          <h4>Добавить чат по ссылке</h4>
                          <div className="form-inline">
                            <input
                              type="text"
                              value={addingChatForGroup === group.group_id ? newChatLink : ''}
                              onChange={(e) => {
                                setAddingChatForGroup(group.group_id)
                                setNewChatLink(e.target.value)
                              }}
                              placeholder="https://t.me/..."
                            />
                            <button
                              className="btn-primary small"
                              onClick={() => {
                                setAddingChatForGroup(group.group_id)
                                void handleAddChat(group)
                              }}
                              disabled={addChatMutation.isLoading}
                            >
                              {addChatMutation.isLoading ? 'Добавление...' : 'Добавить чат'}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div>Списков чатов пока нет</div>
          )}
        </GlassCard>
      </div>
    </Layout>
  )
}


