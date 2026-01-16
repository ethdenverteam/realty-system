import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import './BotChats.css'

export default function AdminBotChats() {
  const [chats, setChats] = useState([])
  const [config, setConfig] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [formData, setFormData] = useState({
    chat_link: '',
    filter_type: '',
    rooms_types: [],
    districts: [],
    price_min: '',
    price_max: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [chatsRes, configRes] = await Promise.all([
        api.get('/admin/dashboard/bot-chats/list'),
        api.get('/admin/dashboard/bot-chats/config')
      ])
      setChats(chatsRes.data)
      setConfig(configRes.data)
    } catch (err) {
      setError('Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
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
      await api.post('/admin/dashboard/bot-chats', {
        chat_link: formData.chat_link,
        filters
      })
      setSuccess('Чат успешно добавлен')
      setShowAddModal(false)
      setFormData({
        chat_link: '',
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
    if (filters.rooms_types?.length) {
      parts.push(`Комнаты: ${filters.rooms_types.join(', ')}`)
    }
    if (filters.districts?.length) {
      parts.push(`Районы: ${filters.districts.join(', ')}`)
    }
    if (filters.price_min || filters.price_max) {
      parts.push(`Цена: ${filters.price_min || 0} - ${filters.price_max || '∞'}`)
    }
    return parts.length ? parts.join(' | ') : (chat.category || 'Нет фильтров')
  }

  return (
    <Layout 
      title="Чаты бота" 
      isAdmin
      headerActions={
        <button 
          className="header-icon-btn" 
          onClick={() => setShowAddModal(true)}
          aria-label="Добавить чат"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M10 4V16M4 10H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
      }
    >
      <div className="bot-chats-page">
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {showAddModal && (
          <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Добавить чат</h2>
                <button className="modal-close" onClick={() => setShowAddModal(false)}>×</button>
              </div>
              <form onSubmit={handleAddChat} className="modal-form">
                <div className="form-group">
                  <label className="form-label">Ссылка на чат</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.chat_link}
                    onChange={(e) => setFormData({...formData, chat_link: e.target.value})}
                    placeholder="https://t.me/chatname или @chatname"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Тип фильтра</label>
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

                {formData.filter_type === 'district' && config && (
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
                    >
                      {Object.keys(config.districts || {}).map(d => (
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

        <div className="card">
          <h2 className="card-title">Список чатов</h2>
          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : chats.length === 0 ? (
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
                  {chats.map(chat => (
                    <tr key={chat.chat_id}>
                      <td>
                        <strong>{chat.title}</strong>
                        <br />
                        <small>{chat.telegram_chat_id}</small>
                      </td>
                      <td>{chat.type}</td>
                      <td><small>{getFiltersText(chat)}</small></td>
                      <td>
                        {chat.is_active ? (
                          <span className="badge badge-success">Активен</span>
                        ) : (
                          <span className="badge badge-danger">Неактивен</span>
                        )}
                      </td>
                      <td>
                        <button 
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(chat.chat_id)}
                        >
                          Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}

