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

  useEffect(() => {
    void loadObjects()
  }, [statusFilter])

  const loadObjects = async (): Promise<void> => {
    try {
      setLoading(true)
      const params: { status?: string } = {}
      if (statusFilter) params.status = statusFilter
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
                <div key={obj.object_id} className="object-card">
                  <div className="object-header">
                    <h3 className="object-id">{obj.object_id}</h3>
                    <span
                      className={`badge badge-${
                        obj.status === 'опубликовано'
                          ? 'success'
                          : obj.status === 'черновик'
                            ? 'warning'
                            : 'secondary'
                      }`}
                    >
                      {obj.status}
                    </span>
                  </div>
                  <div className="object-details">
                    {obj.rooms_type && (
                      <div>
                        <strong>Тип:</strong> {obj.rooms_type}
                      </div>
                    )}
                    {obj.price > 0 && (
                      <div>
                        <strong>Цена:</strong> {obj.price} тыс. руб.
                      </div>
                    )}
                    {obj.area && (
                      <div>
                        <strong>Площадь:</strong> {obj.area} м²
                      </div>
                    )}
                    {obj.floor && (
                      <div>
                        <strong>Этаж:</strong> {obj.floor}
                      </div>
                    )}
                    {(obj.districts_json?.length || 0) > 0 && (
                      <div>
                        <strong>Районы:</strong> {(obj.districts_json || []).join(', ')}
                      </div>
                    )}
                  </div>
                  {obj.comment && (
                    <div className="object-comment">
                      {obj.comment.substring(0, 100)}
                      {obj.comment.length > 100 ? '...' : ''}
                    </div>
                  )}
                  <div className="object-actions">
                    <Link to={`/user/dashboard/objects/${obj.object_id}`} className="btn btn-sm btn-primary">
                      Просмотр
                    </Link>
                    <button
                      onClick={async () => {
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
                            alert('Объект успешно опубликован!')
                            await loadObjects()
                          } else {
                            alert(res.data.error || 'Ошибка публикации')
                          }
                        } catch (err: unknown) {
                          let message = 'Ошибка публикации'
                          if (axios.isAxiosError<ApiErrorResponse>(err)) {
                            message = err.response?.data?.error || err.message || message
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


