import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import './BotChats.css'

export default function AdminBotChats() {
  const [chats, setChats] = useState([])
  const [config, setConfig] = useState(null)
  const [districts, setDistricts] = useState({})
  const [showAddModal, setShowAddModal] = useState(false)
  const [showFetchModal, setShowFetchModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [fetching, setFetching] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [fetchedChats, setFetchedChats] = useState({ groups: [], users: [] })
  const [chatFilter, setChatFilter] = useState('all') // all, groups, users

  const [formData, setFormData] = useState({
    chat_id: '',
    chat_title: '',
    filter_type: '',
    rooms_types: [],
    districts: [],
    price_min: '',
    price_max: ''
  })

  const [newDistrict, setNewDistrict] = useState('')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError('')
      const [chatsRes, configRes, districtsRes] = await Promise.all([
        api.get('/admin/dashboard/bot-chats/list'),
        api.get('/admin/dashboard/bot-chats/config'),
        api.get('/admin/dashboard/bot-chats/districts')
      ])
      setChats(chatsRes.data)
      setConfig(configRes.data)
      // Ensure districts is an object, not null or undefined
      const districtsData = districtsRes.data.districts || {}
      setDistricts(districtsData)
      // Also update config districts if config exists
      if (configRes.data) {
        setConfig({ ...configRes.data, districts: districtsData })
      }
    } catch (err) {
      console.error('Error loading data:', err)
      setError(err.response?.data?.error || 'Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  const loadDistricts = async () => {
    try {
      const districtsRes = await api.get('/admin/dashboard/bot-chats/districts')
      setDistricts(districtsRes.data.districts || {})
    } catch (err) {
      console.error('Error loading districts:', err)
    }
  }

  const handleFetchChats = async () => {
    try {
      setFetching(true)
      setError('')
      const response = await api.post('/admin/dashboard/bot-chats/fetch', { stop_bot: true }, {
        headers: {
          'Content-Type': 'application/json'
        }
      })
      setFetchedChats(response.data)
      setShowFetchModal(true)
      if (response.data.warning) {
        setError(response.data.warning)
      }
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.details || 'Ошибка при получении чатов')
    } finally {
      setFetching(false)
    }
  }

  const handleSelectChat = (chat) => {
    setFormData({
      ...formData,
      chat_id: chat.id,
      chat_title: chat.title
    })
    setShowFetchModal(false)
    setShowAddModal(true)
  }

  const handleAddChat = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    let filters = {}
    if (formData.filter_type === 'rooms') {
      filters.rooms_types = formData.rooms_types
    } else if (formData.filter_type === 'district') {
      filters.districts = formData.districts
    } else if (formData.filter_type === 'price') {
      filters.price_min = formData.price_min ? parseFloat(formData.price_min) : null
      filters.price_max = formData.price_max ? parseFloat(formData.price_max) : null
    }

    try {
      // Use chat_id as-is - it can be ID, username, or link
      const chatLink = formData.chat_id.trim()
      
      await api.post('/admin/dashboard/bot-chats', {
        chat_link: chatLink,
        filters
      })
      setSuccess('Чат успешно добавлен')
      setShowAddModal(false)
      setFormData({
        chat_id: '',
        chat_title: '',
        filter_type: '',
        rooms_types: [],
        districts: [],
        price_min: '',
        price_max: ''
      })
      loadData()
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка при добавлении чата')
    }
  }

  const handleAddDistrict = async (e) => {
    e.preventDefault()
    if (!newDistrict.trim()) return

    try {
      setError('')
      const response = await api.post('/admin/dashboard/bot-chats/districts', {
        name: newDistrict.trim()
      })
      setSuccess('Район успешно добавлен')
      setNewDistrict('')
      // Обновляем список районов из ответа
      const districtsData = response.data.districts || {}
      setDistricts(districtsData)
      // Также обновляем конфиг для формы
      if (config) {
        setConfig({ ...config, districts: districtsData })
      }
      // Перезагружаем данные для уверенности
      await loadDistricts()
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка при добавлении района')
    }
  }

  const handleDeleteDistrict = async (districtName) => {
    if (!confirm(`Удалить район "${districtName}"?`)) return

    try {
      setError('')
      const response = await api.delete(`/admin/dashboard/bot-chats/districts/${encodeURIComponent(districtName)}`)
      setSuccess('Район успешно удален')
      // Обновляем список районов из ответа
      const districtsData = response.data.districts || {}
      setDistricts(districtsData)
      // Также обновляем конфиг для формы
      if (config) {
        setConfig({ ...config, districts: districtsData })
      }
      // Перезагружаем данные для уверенности
      await loadDistricts()
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка при удалении района')
    }
  }

  const handleTestPublish = async (chatId) => {
    if (!confirm('Отправить тестовое сообщение в этот чат?')) return

    try {
      setError('')
      setSuccess('')
      const response = await api.post(`/admin/dashboard/bot-chats/${chatId}/test-publish`)
      setSuccess('Тестовое сообщение отправлено успешно')
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.details || 'Ошибка при отправке тестового сообщения')
    }
  }

  const handleDelete = async (chatId) => {
    if (!confirm('Удалить этот чат?')) return

    try {
      await api.delete(`/admin/dashboard/bot-chats/${chatId}`)
      setSuccess('Чат удален')
      loadData()
    } catch (err) {
      setError('Ошибка при удалении')
    }
  }

  const getFiltersText = (chat) => {
    const filters = chat.filters_json || {}
    const parts = []
    
    // Show filter type and values
    if (filters.rooms_types?.length) {
      parts.push(`Комнаты: ${filters.rooms_types.join(', ')}`)
    }
    if (filters.districts?.length) {
      parts.push(`Районы: ${filters.districts.join(', ')}`)
    }
    if (filters.price_min || filters.price_max) {
      parts.push(`Цена: ${filters.price_min || 0} - ${filters.price_max || '∞'} тыс. руб.`)
    }
    
    // If no filters_json but has category (legacy)
    if (parts.length === 0 && chat.category) {
      // Parse legacy category format
      if (chat.category.startsWith('rooms_')) {
        parts.push(`Комнаты: ${chat.category.replace('rooms_', '')}`)
      } else if (chat.category.startsWith('district_')) {
        parts.push(`Районы: ${chat.category.replace('district_', '')}`)
      } else if (chat.category.startsWith('price_')) {
        const priceParts = chat.category.replace('price_', '').split('_')
        if (priceParts.length === 2) {
          parts.push(`Цена: ${priceParts[0]} - ${priceParts[1]} тыс. руб.`)
        }
      } else {
        parts.push(chat.category)
      }
    }
    
    return parts.length ? parts.join(' | ') : 'Нет фильтров'
  }
  
  const getChatTypeLabel = (type) => {
    const typeMap = {
      'group': 'Группа',
      'supergroup': 'Супергруппа',
      'channel': 'Канал',
      'private': 'Личный'
    }
    return typeMap[type] || type
  }

  const filteredChats = chatFilter === 'all' 
    ? chats 
    : chatFilter === 'groups' 
    ? chats.filter(c => ['group', 'supergroup', 'channel'].includes(c.type))
    : chats.filter(c => c.type === 'private')

  return (
    <Layout 
      title="Управление чатами и районами бота" 
      isAdmin
      headerActions={
        <Link to="/admin/dashboard" className="btn btn-secondary">
          ← Назад в дашборд
        </Link>
      }
    >
      <div className="bot-chats-page">
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {/* Fetch Chats Modal */}
        {showFetchModal && (
          <div className="modal-overlay" onClick={() => setShowFetchModal(false)}>
            <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Выберите чат для добавления</h2>
                <button className="modal-close" onClick={() => setShowFetchModal(false)}>×</button>
              </div>
              <div className="modal-content">
                <div className="chat-filter-tabs">
                  <button 
                    className={`tab ${chatFilter === 'groups' ? 'active' : ''}`}
                    onClick={() => setChatFilter('groups')}
                  >
                    Группы ({fetchedChats.groups.length})
                  </button>
                  <button 
                    className={`tab ${chatFilter === 'users' ? 'active' : ''}`}
                    onClick={() => setChatFilter('users')}
                  >
                    Пользователи ({fetchedChats.users.length})
                  </button>
                </div>
                <div className="chat-list">
                  {(chatFilter === 'groups' ? fetchedChats.groups : fetchedChats.users).map(chat => (
                    <div 
                      key={chat.id} 
                      className="chat-item"
                      onClick={() => handleSelectChat(chat)}
                    >
                      <div className="chat-item-title">{chat.title}</div>
                      <div className="chat-item-meta">
                        <span className="chat-item-type">{getChatTypeLabel(chat.type)}</span>
                        <span className="chat-item-id">ID: {chat.id}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Add Chat Modal */}
        {showAddModal && (
          <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Добавить чат</h2>
                <button className="modal-close" onClick={() => setShowAddModal(false)}>×</button>
              </div>
              <form onSubmit={handleAddChat} className="modal-form">
                {formData.chat_title && (
                  <div className="form-group">
                    <label className="form-label">Выбранный чат</label>
                    <div className="selected-chat">
                      <strong>{formData.chat_title}</strong>
                      <small>ID: {formData.chat_id}</small>
                    </div>
                  </div>
                )}

                {!formData.chat_title && (
                  <div className="form-group">
                    <label className="form-label">Ссылка на чат или ID</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.chat_id}
                      onChange={(e) => setFormData({...formData, chat_id: e.target.value})}
                      placeholder="https://t.me/chatname, @chatname или ID чата (например: -1002632748579)"
                      required
                    />
                    <button 
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setShowAddModal(false)
                        handleFetchChats()
                      }}
                    >
                      Получить чаты
                    </button>
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Тип категории связи</label>
                  <select
                    className="form-input"
                    value={formData.filter_type}
                    onChange={(e) => setFormData({...formData, filter_type: e.target.value})}
                    required
                  >
                    <option value="">Выберите тип</option>
                    <option value="rooms">По типу комнат</option>
                    <option value="district">По району</option>
                    <option value="price">По диапазону цен</option>
                  </select>
                </div>

                {formData.filter_type === 'rooms' && config && (
                  <div className="form-group">
                    <label className="form-label">Типы комнат</label>
                    <div className="checkbox-group">
                      {config.rooms_types.map(rt => (
                        <label key={rt} className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={formData.rooms_types.includes(rt)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setFormData({...formData, rooms_types: [...formData.rooms_types, rt]})
                              } else {
                                setFormData({...formData, rooms_types: formData.rooms_types.filter(x => x !== rt)})
                              }
                            }}
                          />
                          <span>{rt}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {formData.filter_type === 'district' && (
                  <div className="form-group">
                    <label className="form-label">Районы</label>
                    <select
                      className="form-input"
                      multiple
                      value={formData.districts}
                      onChange={(e) => {
                        const selected = Array.from(e.target.selectedOptions, opt => opt.value)
                        setFormData({...formData, districts: selected})
                      }}
                      required
                    >
                      {Object.keys(districts).map(d => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                    <small className="form-hint">Удерживайте Ctrl для выбора нескольких</small>
                  </div>
                )}

                {formData.filter_type === 'price' && (
                  <>
                    <div className="form-group">
                      <label className="form-label">Минимальная цена (тыс. руб.)</label>
                      <input
                        type="number"
                        className="form-input"
                        value={formData.price_min}
                        onChange={(e) => setFormData({...formData, price_min: e.target.value})}
                        min="0"
                        step="100"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Максимальная цена (тыс. руб.)</label>
                      <input
                        type="number"
                        className="form-input"
                        value={formData.price_max}
                        onChange={(e) => setFormData({...formData, price_max: e.target.value})}
                        min="0"
                        step="100"
                        required
                      />
                    </div>
                  </>
                )}

                <div className="modal-actions">
                  <button type="submit" className="btn btn-primary">Добавить</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Отмена</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Districts Management Card - Always visible */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Управление районами</h2>
          </div>
          <div className="card-content">
            <form onSubmit={handleAddDistrict} className="form-inline">
              <input
                type="text"
                className="form-input"
                value={newDistrict}
                onChange={(e) => setNewDistrict(e.target.value)}
                placeholder="Название района"
              />
              <button type="submit" className="btn btn-primary">Добавить район</button>
            </form>
            <div className="districts-list">
              {Object.keys(districts).length === 0 ? (
                <div className="empty-state">Нет районов. Добавьте первый район.</div>
              ) : (
                <div className="districts-grid">
                  {Object.keys(districts).map(district => (
                    <div key={district} className="district-item">
                      <span>{district}</span>
                      <button 
                        className="btn btn-sm btn-danger"
                        onClick={() => handleDeleteDistrict(district)}
                      >
                        Удалить
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Chats List Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Список чатов</h2>
            <div className="card-actions">
              <button 
                className="btn btn-secondary"
                onClick={handleFetchChats}
                disabled={fetching}
              >
                {fetching ? 'Загрузка...' : 'Получить чаты'}
              </button>
              <button 
                className="btn btn-primary"
                onClick={() => setShowAddModal(true)}
              >
                Добавить чат
              </button>
            </div>
          </div>
          <div className="card-content">
            <div className="chat-filter-tabs">
              <button 
                className={`tab ${chatFilter === 'all' ? 'active' : ''}`}
                onClick={() => setChatFilter('all')}
              >
                Все ({chats.length})
              </button>
              <button 
                className={`tab ${chatFilter === 'groups' ? 'active' : ''}`}
                onClick={() => setChatFilter('groups')}
              >
                Группы ({chats.filter(c => ['group', 'supergroup', 'channel'].includes(c.type)).length})
              </button>
              <button 
                className={`tab ${chatFilter === 'users' ? 'active' : ''}`}
                onClick={() => setChatFilter('users')}
              >
                Пользователи ({chats.filter(c => c.type === 'private').length})
              </button>
            </div>
            {loading ? (
              <div className="loading">Загрузка...</div>
            ) : filteredChats.length === 0 ? (
              <div className="empty-state">Нет чатов. Добавьте первый чат.</div>
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Название</th>
                      <th>Тип</th>
                      <th>Фильтры</th>
                      <th>Статус</th>
                      <th>Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredChats.map(chat => (
                      <tr key={chat.chat_id}>
                        <td>
                          <strong>{chat.title}</strong>
                          <br />
                          <small>{chat.telegram_chat_id}</small>
                        </td>
                        <td>{getFiltersText(chat) !== 'Нет фильтров' ? getFiltersText(chat) : getChatTypeLabel(chat.type)}</td>
                        <td><small>{getFiltersText(chat)}</small></td>
                        <td>
                          {chat.is_active ? (
                            <span className="badge badge-success">Активен</span>
                          ) : (
                            <span className="badge badge-danger">Неактивен</span>
                          )}
                        </td>
                        <td>
                          <div className="btn-group">
                            <button 
                              className="btn btn-sm btn-secondary"
                              onClick={() => handleTestPublish(chat.chat_id)}
                              title="Отправить тестовое сообщение в чат"
                            >
                              Тест
                            </button>
                            <button 
                              className="btn btn-sm btn-danger"
                              onClick={() => handleDelete(chat.chat_id)}
                            >
                              Удалить
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}
