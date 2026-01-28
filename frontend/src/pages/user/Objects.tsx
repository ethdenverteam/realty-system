import axios from 'axios'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import type { RealtyObjectListItem, ObjectsListResponse, ApiErrorResponse } from '../../types/models'
import './Objects.css'

export default function UserObjects(): JSX.Element {
  const [objects, setObjects] = useState<RealtyObjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('creation_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [roomsTypeFilter, setRoomsTypeFilter] = useState('')
  const [districtFilter, setDistrictFilter] = useState('')
  const [districts, setDistricts] = useState<string[]>([])

  useEffect(() => {
    void loadDistricts()
  }, [])

  useEffect(() => {
    void loadObjects()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, sortBy, sortOrder, roomsTypeFilter, districtFilter])

  const loadDistricts = async (): Promise<void> => {
    try {
      const res = await api.get<{ districts: string[] }>('/user/dashboard/districts')
      setDistricts(res.data.districts || [])
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error('Error loading districts:', err.response?.data || err.message)
      }
    }
  }

  const loadObjects = async (): Promise<void> => {
    try {
      setLoading(true)
      const params: { status?: string; sort_by?: string; sort_order?: string; rooms_type?: string; district?: string } = {}
      if (statusFilter) params.status = statusFilter
      if (sortBy) params.sort_by = sortBy
      if (sortOrder) params.sort_order = sortOrder
      if (roomsTypeFilter) params.rooms_type = roomsTypeFilter
      if (districtFilter) params.district = districtFilter
      const res = await api.get<ObjectsListResponse>('/user/dashboard/objects/list', { params })
      setObjects(res.data.objects || [])
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error('Error loading objects:', err.response?.data || err.message)
      } else {
        console.error('Error loading objects:', err)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout
      title="Мои объекты"
      headerActions={
        <Link to="/user/dashboard/objects/create" className="header-icon-btn">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M10 4V16M4 10H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </Link>
      }
    >
      <div className="objects-page">
        <div className="card">
          <div className="card-header-row">
            <h2 className="card-title">Список объектов</h2>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <select
                className="form-input form-input-sm"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">Все статусы</option>
                <option value="черновик">Черновики</option>
                <option value="опубликовано">Опубликованные</option>
                <option value="запланировано">Запланированные</option>
                <option value="архив">Архив</option>
              </select>
              <select
                className="form-input form-input-sm"
                value={roomsTypeFilter}
                onChange={(e) => setRoomsTypeFilter(e.target.value)}
              >
                <option value="">Все типы комнат</option>
                <option value="Студия">Студия</option>
                <option value="1к">1к</option>
                <option value="2к">2к</option>
                <option value="3к">3к</option>
                <option value="4+к">4+к</option>
                <option value="Дом">Дом</option>
                <option value="1евро">1евро</option>
                <option value="евро1к">евро1к</option>
                <option value="2евро">2евро</option>
                <option value="евро2к">евро2к</option>
                <option value="3евро">3евро</option>
                <option value="евро3к">евро3к</option>
              </select>
              <select
                className="form-input form-input-sm"
                value={districtFilter}
                onChange={(e) => setDistrictFilter(e.target.value)}
              >
                <option value="">Все районы</option>
                {districts.map((district) => (
                  <option key={district} value={district}>
                    {district}
                  </option>
                ))}
              </select>
              <select
                className="form-input form-input-sm"
                value={`${sortBy}_${sortOrder}`}
                onChange={(e) => {
                  const value = e.target.value
                  // Split from the end to handle sort_by values that contain underscores (like 'creation_date')
                  const lastUnderscoreIndex = value.lastIndexOf('_')
                  if (lastUnderscoreIndex > 0 && lastUnderscoreIndex < value.length - 1) {
                    const newSortBy = value.substring(0, lastUnderscoreIndex)
                    const newSortOrder = value.substring(lastUnderscoreIndex + 1) as 'asc' | 'desc'
                    // Update both values separately to ensure React sees the change
                    if (newSortBy !== sortBy || newSortOrder !== sortOrder) {
                      setSortBy(newSortBy)
                      setSortOrder(newSortOrder)
                    }
                  }
                }}
              >
                <option value="creation_date_desc">Новые сначала</option>
                <option value="creation_date_asc">Старые сначала</option>
                <option value="price_desc">Цена: дороже</option>
                <option value="price_asc">Цена: дешевле</option>
              </select>
            </div>
          </div>

          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : objects.length === 0 ? (
            <div className="empty-state">
              У вас пока нет объектов. <Link to="/user/dashboard/objects/create">Создайте первый объект</Link>
            </div>
          ) : (
            <div className="objects-list">
              {objects.map((obj) => (
                <div 
                  key={obj.object_id} 
                  className="object-card compact"
                  onClick={(e) => {
                    // Добавляем glow эффект при клике на карточку
                    const card = e.currentTarget
                    card.classList.add('glow-active')
                    setTimeout(() => {
                      card.classList.remove('glow-active')
                    }, 400)
                  }}
                >
                  <div className="object-details-compact">
                    {obj.rooms_type && (
                      <div className="object-detail-item">
                        {obj.rooms_type}
                      </div>
                    )}
                    {obj.price > 0 && (
                      <div className="object-detail-item">
                        {obj.price} тыс. руб.
                      </div>
                    )}
                    {obj.area && (
                      <div className="object-detail-item">
                        {obj.area} м²
                      </div>
                    )}
                    {(obj.districts_json?.length || 0) > 0 && (
                      <div className="object-detail-item">
                        {(obj.districts_json || []).join(', ')}
                      </div>
                    )}
                  </div>
                  <div className="object-actions">
                    <Link to={`/user/dashboard/objects/${obj.object_id}`} className="btn btn-sm btn-primary">
                      Просмотр
                    </Link>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation()
                        if (!obj.can_publish) {
                          alert(obj.last_publication ? 
                            `Объект был опубликован менее 24 часов назад. Последняя публикация: ${new Date(obj.last_publication).toLocaleString('ru-RU')}` :
                            'Объект нельзя опубликовать сейчас')
                          return
                        }
                        if (!confirm('Вы уверены, что хотите опубликовать этот объект через бота?')) {
                          return
                        }
                        try {
                          const res = await api.post('/user/dashboard/objects/publish', {
                            object_id: obj.object_id,
                          })
                          if (res.data.success) {
                            const message = res.data.message || `Объект успешно опубликован в ${res.data.published_count || 0} чатов!`
                            alert(message)
                            await loadObjects()
                          } else {
                            alert(res.data.error || 'Ошибка публикации')
                          }
                        } catch (err: unknown) {
                          let message = 'Ошибка публикации'
                          if (axios.isAxiosError<ApiErrorResponse>(err)) {
                            message = err.response?.data?.error || err.response?.data?.message || err.message || message
                          }
                          alert(message)
                        }
                      }}
                      className="btn btn-sm btn-secondary"
                      title={!obj.can_publish && obj.last_publication ? 
                        `Объект был опубликован менее 24 часов назад. Последняя публикация: ${new Date(obj.last_publication).toLocaleString('ru-RU')}` : 
                        undefined}
                      disabled={!obj.can_publish}
                    >
                      {!obj.can_publish ? 'Опубликовать (нельзя)' : 'Опубликовать'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}


