import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { GlassButton } from '../../components/GlassButton'
import { useApiData } from '../../hooks/useApiData'
import { useApiMutation } from '../../hooks/useApiMutation'
import { getErrorMessage, logError } from '../../utils/errorHandler'
import api from '../../utils/api'
import './ChatSubscriptions.css'
import { useAuth } from '../../contexts/AuthContext'

interface TelegramAccount {
  account_id: number
  phone: string
  is_active: boolean
}

interface ChatGroup {
  group_id: number
  name: string
  description?: string
  chat_ids: number[]
  chat_links?: string[]
  created_at: string
  updated_at: string
}

interface SubscriptionTask {
  task_id: number
  user_id: number
  account_id: number
  group_id: number
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'flood_wait'
  current_index: number
  total_chats: number
  successful_count: number
  flood_count: number
  flood_wait_until: string | null
  result: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  chat_links: string[]
  estimated_completion: string | null
}

export default function ChatSubscriptions(): JSX.Element {
  const { user } = useAuth()
  const [groupName, setGroupName] = useState('')
  const [chatLinks, setChatLinks] = useState('')
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [intervalMode, setIntervalMode] = useState<'safe' | 'aggressive'>('safe')

  // Загрузка данных
  const { data: accounts, loading: accountsLoading } = useApiData<TelegramAccount[]>({
    url: '/accounts',
    errorContext: 'Loading accounts',
  })

  const { data: groups, loading: groupsLoading, reload: reloadGroups } = useApiData<ChatGroup[]>({
    url: '/chat-subscriptions/groups',
    errorContext: 'Loading groups',
  })

  const { data: tasks, loading: tasksLoading, reload: reloadTasks } = useApiData<SubscriptionTask[]>({
    url: '/chat-subscriptions/tasks',
    errorContext: 'Loading tasks',
  })

  // Мутации
  const createGroupMutation = useApiMutation<ChatGroup>({
    url: '/chat-subscriptions/groups',
    method: 'POST',
    onSuccess: () => {
      setGroupName('')
      setChatLinks('')
      reloadGroups()
    },
  })

  const startSubscriptionMutation = useApiMutation<SubscriptionTask>({
    url: '/chat-subscriptions/tasks',
    method: 'POST',
    onSuccess: (data) => {
      setSelectedTaskId(data.task_id)
      reloadTasks()
    },
  })

  const continueSubscriptionMutation = useApiMutation<SubscriptionTask>({
    url: `/chat-subscriptions/tasks/${selectedTaskId}/continue`,
    method: 'POST',
    onSuccess: () => {
      reloadTasks()
    },
  })

  const retrySubscriptionMutation = useApiMutation<SubscriptionTask>({
    url: `/chat-subscriptions/tasks/${selectedTaskId}/retry`,
    method: 'POST',
    onSuccess: () => {
      reloadTasks()
    },
  })

  const cancelSubscriptionMutation = useApiMutation<SubscriptionTask>({
    url: `/chat-subscriptions/tasks/${selectedTaskId}/cancel`,
    method: 'POST',
    onSuccess: () => {
      setSelectedTaskId(null)
      reloadTasks()
    },
  })

  const pauseSubscriptionMutation = useApiMutation<SubscriptionTask>({
    url: `/chat-subscriptions/tasks/${selectedTaskId}/pause`,
    method: 'POST',
    onSuccess: () => {
      reloadTasks()
    },
  })

  const deleteGroupMutation = useApiMutation({
    url: `/chat-subscriptions/groups/${selectedGroupId}`,
    method: 'DELETE',
    onSuccess: () => {
      reloadGroups()
      setSelectedGroupId(null)
    },
  })

  // Получение текущей задачи
  const currentTask = tasks?.find(t => t.task_id === selectedTaskId) || tasks?.find(t => t.status === 'processing' || t.status === 'flood_wait')

  // Автообновление статуса каждые 5 секунд для активных задач
  useEffect(() => {
    if (currentTask && (currentTask.status === 'processing' || currentTask.status === 'flood_wait')) {
      const interval = setInterval(() => {
        reloadTasks()
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [currentTask?.status, reloadTasks])

  const getAccountLabel = (accountId: number | null | undefined): string => {
    if (!accountId) return '-'
    const acc = accounts?.find((a) => a.account_id === accountId)
    if (!acc) return `ID ${accountId}`
    return `${acc.phone} ${acc.is_active ? '(активен)' : '(неактивен)'}`
  }

  const handleCreateGroup = async () => {
    if (!groupName.trim()) {
      alert('Введите название списка')
      return
    }
    if (!chatLinks.trim()) {
      alert('Введите ссылки на чаты')
      return
    }

    try {
      await createGroupMutation.mutate({
        name: groupName,
        links: chatLinks,
      })
    } catch (error) {
      logError(error, 'Creating chat group')
      alert(getErrorMessage(error, 'Ошибка создания списка'))
    }
  }

  const handleStartSubscription = async () => {
    if (!selectedAccountId) {
      alert('Выберите аккаунт')
      return
    }
    if (!selectedGroupId) {
      alert('Выберите список чатов')
      return
    }

    try {
      await startSubscriptionMutation.mutate({
        account_id: selectedAccountId,
        group_id: selectedGroupId,
        interval_mode: intervalMode,
      })
    } catch (error) {
      logError(error, 'Starting subscription')
      alert(getErrorMessage(error, 'Ошибка запуска подписки'))
    }
  }

  const handleContinueSubscription = async () => {
    if (!selectedTaskId) {
      alert('Выберите задачу')
      return
    }

    try {
      await continueSubscriptionMutation.mutate({})
    } catch (error) {
      logError(error, 'Continuing subscription')
      alert(getErrorMessage(error, 'Ошибка продолжения подписки'))
    }
  }

  const handleCancelSubscription = async (taskId: number) => {
    if (!confirm('Отменить эту задачу подписки? Прогресс будет потерян.')) {
      return
    }
    setSelectedTaskId(taskId)
    try {
      await cancelSubscriptionMutation.mutate({})
    } catch (error) {
      logError(error, 'Canceling subscription')
      alert(getErrorMessage(error, 'Ошибка отмены задачи'))
    }
  }

  const handlePauseSubscription = async (taskId: number) => {
    setSelectedTaskId(taskId)
    try {
      await pauseSubscriptionMutation.mutate({})
    } catch (error) {
      logError(error, 'Pausing subscription')
      alert(getErrorMessage(error, 'Ошибка паузы задачи'))
    }
  }

  const handleRetrySubscription = async (taskId: number) => {
    setSelectedTaskId(taskId)
    try {
      await retrySubscriptionMutation.mutate({})
    } catch (error) {
      logError(error, 'Retrying subscription')
      alert(getErrorMessage(error, 'Ошибка возобновления задачи'))
    }
  }

  const handleDeleteGroup = async (groupId: number) => {
    if (!confirm('Удалить этот список чатов?')) {
      return
    }
    setSelectedGroupId(groupId)
    try {
      await deleteGroupMutation.mutate({})
    } catch (error) {
      logError(error, 'Deleting group')
      alert(getErrorMessage(error, 'Ошибка удаления списка'))
    }
  }

  const getStatusText = (task: SubscriptionTask): string => {
    switch (task.status) {
      case 'pending':
        return 'Ожидание'
      case 'processing':
        return 'В процессе'
      case 'completed':
        return 'Завершено'
      case 'failed':
        return 'Ошибка'
      case 'flood_wait':
        return 'Ожидание после flood'
      default:
        return task.status
    }
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'pending':
        return '#ffa500'
      case 'processing':
        return '#007bff'
      case 'completed':
        return '#28a745'
      case 'failed':
        return '#dc3545'
      case 'flood_wait':
        return '#ff6b6b'
      default:
        return '#6c757d'
    }
  }

  const myGroups = (groups || []).filter((g) => !user || g.user_id === user.user_id)
  const publicGroups = (groups || []).filter((g) => user && g.user_id !== user.user_id)

  return (
    <Layout title="Подписка на чаты">
      <div className="chat-subscriptions-page">
        {/* Создание списка чатов */}
        <GlassCard className="create-group-section">
          <h2>Создать список чатов</h2>
          <div className="form-group">
            <label>Название списка:</label>
            <input
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder="Например: Список чатов 1"
            />
          </div>
          <div className="form-group">
            <label>Ссылки на чаты (каждая строка - ссылка):</label>
            <textarea
              value={chatLinks}
              onChange={(e) => setChatLinks(e.target.value)}
              placeholder="https://t.me/+Poqjzr81Y3MzMTk6&#10;https://t.me/+TmyIkz1R8fY2ZGIy&#10;https://t.me/+2vLkee9ANCE1OTNi"
              rows={10}
            />
          </div>
          <GlassButton
            onClick={handleCreateGroup}
            disabled={createGroupMutation.isLoading}
          >
            {createGroupMutation.isLoading ? 'Создание...' : 'Сохранить список'}
          </GlassButton>
        </GlassCard>

        {/* Список сохраненных групп пользователя */}
        <GlassCard className="groups-section">
          <h2>Мои сохраненные списки чатов</h2>
          {groupsLoading ? (
            <div>Загрузка...</div>
          ) : myGroups && myGroups.length > 0 ? (
            <div className="groups-list">
              {myGroups.map((group) => (
                <div key={group.group_id} className="group-item">
                  <div className="group-header">
                    <h3>{group.name}</h3>
                    <div className="group-actions">
                      <button
                        className="btn-delete"
                        onClick={() => handleDeleteGroup(group.group_id)}
                        disabled={deleteGroupMutation.isLoading}
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                  <div className="group-info">
                    <span>Чатов: {group.chat_ids.length}</span>
                    <span>Создан: {new Date(group.created_at).toLocaleString('ru-RU')}</span>
                  </div>
                  <div className="group-select">
                    <input
                      type="radio"
                      name="selectedGroup"
                      checked={selectedGroupId === group.group_id}
                      onChange={() => setSelectedGroupId(group.group_id)}
                    />
                    <label>Использовать для подписки</label>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div>Нет сохраненных списков</div>
          )}
        </GlassCard>

        {/* Публичные списки чатов */}
        {publicGroups && publicGroups.length > 0 && (
          <GlassCard className="groups-section">
            <h2>Общие списки чатов (публичные)</h2>
            <div className="groups-list">
              {publicGroups.map((group) => (
                <div key={group.group_id} className="group-item">
                  <div className="group-header">
                    <h3>{group.name}</h3>
                    <div className="group-info">
                      <span>Владелец user_id: {group.user_id}</span>
                      <span>Чатов: {group.chat_ids.length}</span>
                    </div>
                  </div>
                  <div className="group-select">
                    <input
                      type="radio"
                      name="selectedGroup"
                      checked={selectedGroupId === group.group_id}
                      onChange={() => setSelectedGroupId(group.group_id)}
                    />
                    <label>Использовать для подписки</label>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        )}

        {/* Запуск подписки */}
        <GlassCard className="subscription-section">
          <h2>Запустить подписку</h2>
          <div className="form-group">
            <label>Выберите аккаунт:</label>
            <select
              value={selectedAccountId || ''}
              onChange={(e) => setSelectedAccountId(e.target.value ? parseInt(e.target.value) : null)}
              disabled={accountsLoading}
            >
              <option value="">-- Выберите аккаунт --</option>
              {accounts?.map((account) => (
                <option key={account.account_id} value={account.account_id}>
                  {account.phone} {account.is_active ? '(активен)' : '(неактивен)'}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Режим интервала:</label>
            <select
              value={intervalMode}
              onChange={(e) => setIntervalMode(e.target.value === 'aggressive' ? 'aggressive' : 'safe')}
            >
              <option value="safe">Safe — ~10 минут между чатами</option>
              <option value="aggressive">Aggressive — ~2 минуты между чатами</option>
            </select>
          </div>
          <div className="form-group">
            <label>Выберите список чатов:</label>
            <select
              value={selectedGroupId || ''}
              onChange={(e) => setSelectedGroupId(e.target.value ? parseInt(e.target.value) : null)}
              disabled={groupsLoading}
            >
              <option value="">-- Выберите список --</option>
              {groups?.map((group) => (
                <option key={group.group_id} value={group.group_id}>
                  {group.name} ({group.chat_ids.length} чатов)
                </option>
              ))}
            </select>
          </div>
          <GlassButton
            onClick={handleStartSubscription}
            disabled={startSubscriptionMutation.isLoading || !selectedAccountId || !selectedGroupId}
          >
            {startSubscriptionMutation.isLoading ? 'Запуск...' : 'Начать подписку'}
          </GlassButton>
        </GlassCard>

        {/* Статус подписки */}
        {currentTask && (
          <GlassCard className="status-section">
            <h2>Статус подписки</h2>
            <div className="status-info">
              <div className="status-header">
                <span className="status-badge" style={{ backgroundColor: getStatusColor(currentTask.status) }}>
                  {getStatusText(currentTask)}
                </span>
                <div className="status-actions">
                  {(currentTask.status === 'processing' || currentTask.status === 'pending') && (
                    <GlassButton
                      onClick={() => handlePauseSubscription(currentTask.task_id)}
                      disabled={pauseSubscriptionMutation.isLoading}
                      small
                    >
                      {pauseSubscriptionMutation.isLoading ? 'Пауза...' : 'Пауза'}
                    </GlassButton>
                  )}
                  {(currentTask.status === 'processing' ||
                    currentTask.status === 'pending' ||
                    currentTask.status === 'flood_wait') && (
                    <GlassButton
                      onClick={() => handleCancelSubscription(currentTask.task_id)}
                      disabled={cancelSubscriptionMutation.isLoading}
                      small
                      style={{ backgroundColor: '#dc3545' }}
                    >
                      {cancelSubscriptionMutation.isLoading ? 'Отменить...' : 'Отменить'}
                    </GlassButton>
                  )}
                  <GlassButton onClick={() => reloadTasks()} disabled={tasksLoading} small>
                    Обновить статус
                  </GlassButton>
                </div>
              </div>
              <div className="status-account">
                Аккаунт: {getAccountLabel(currentTask.account_id)}
              </div>
              <div className="progress-info">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${(currentTask.successful_count / currentTask.total_chats) * 100}%` }}
                  />
                </div>
                <div className="progress-text">
                  {currentTask.successful_count}/{currentTask.total_chats} чатов подписано
                </div>
              </div>
              {currentTask.estimated_completion && (
                <div className="estimated-time">
                  Расчетное время завершения: {currentTask.estimated_completion}
                </div>
              )}
              {currentTask.result && (
                <div className="result-message">
                  {currentTask.result}
                </div>
              )}
              {currentTask.error_message && (
                <div className="error-message">
                  Ошибка: {currentTask.error_message}
                </div>
              )}
              {currentTask.status === 'failed' && (
                <div className="error-actions">
                  <GlassButton
                    onClick={() => handleRetrySubscription(currentTask.task_id)}
                    disabled={retrySubscriptionMutation.isLoading}
                  >
                    {retrySubscriptionMutation.isLoading ? 'Возобновление...' : 'Попробовать возобновить'}
                  </GlassButton>
                </div>
              )}
              {currentTask.status === 'flood_wait' && currentTask.flood_wait_until && (
                <div className="flood-wait-info">
                  <div>Flood ошибка (количество: {currentTask.flood_count})</div>
                  <div>Ожидание до: {new Date(currentTask.flood_wait_until).toLocaleString('ru-RU')}</div>
                  <GlassButton
                    onClick={handleContinueSubscription}
                    disabled={continueSubscriptionMutation.isLoading}
                  >
                    Продолжить подписку
                  </GlassButton>
                </div>
              )}
            </div>
          </GlassCard>
        )}

        {/* История задач */}
        <GlassCard className="tasks-section">
          <h2>История подписок</h2>
          {tasksLoading ? (
            <div>Загрузка...</div>
          ) : tasks && tasks.length > 0 ? (
            <div className="tasks-list">
              {tasks.map((task) => (
                <div
                  key={task.task_id}
                  className={`task-item ${task.task_id === selectedTaskId ? 'selected' : ''}`}
                  onClick={() => setSelectedTaskId(task.task_id)}
                >
                  <div className="task-header">
                    <span className="task-status" style={{ color: getStatusColor(task.status) }}>
                      {getStatusText(task)}
                    </span>
                    <span className="task-date">
                      {new Date(task.created_at).toLocaleString('ru-RU')}
                    </span>
                  </div>
                  <div className="task-progress">
                    {task.successful_count}/{task.total_chats} чатов
                  </div>
                  {task.result && (
                    <div className="task-result">{task.result}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div>Нет задач подписки</div>
          )}
        </GlassCard>
      </div>
    </Layout>
  )
}

