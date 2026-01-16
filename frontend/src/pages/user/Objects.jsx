import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import './Objects.css'

export default function UserObjects() {
  const [objects, setObjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    loadObjects()
  }, [statusFilter])

  const loadObjects = async () => {
    try {
      setLoading(true)
      const params = statusFilter ? { status: statusFilter } : {}
      const res = await api.get('/user/dashboard/objects/list', { params })
      setObjects(res.data.objects || [])
    } catch (err) {
      console.error('Error loading objects:', err)
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
            <path d="M10 4V16M4 10H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
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
              У вас пока нет объектов.{' '}
              <Link to="/user/dashboard/objects/create">Создайте первый объект</Link>
            </div>
          ) : (
            <div className="objects-list">
              {objects.map(obj => (
                <div key={obj.object_id} className="object-card">
                  <div className="object-header">
                    <h3 className="object-id">{obj.object_id}</h3>
                    <span className={`badge badge-${obj.status === 'опубликовано' ? 'success' : obj.status === 'черновик' ? 'warning' : 'secondary'}`}>
                      {obj.status}
                    </span>
                  </div>
                  <div className="object-details">
                    {obj.rooms_type && <div><strong>Тип:</strong> {obj.rooms_type}</div>}
                    {obj.price > 0 && <div><strong>Цена:</strong> {obj.price} тыс. руб.</div>}
                    {obj.area && <div><strong>Площадь:</strong> {obj.area} м²</div>}
                    {obj.floor && <div><strong>Этаж:</strong> {obj.floor}</div>}
                    {obj.districts_json?.length > 0 && (
                      <div><strong>Районы:</strong> {obj.districts_json.join(', ')}</div>
                    )}
                  </div>
                  {obj.comment && (
                    <div className="object-comment">
                      {obj.comment.substring(0, 100)}{obj.comment.length > 100 ? '...' : ''}
                    </div>
                  )}
                  <div className="object-actions">
                    <Link to={`/user/dashboard/objects/${obj.object_id}`} className="btn btn-sm btn-primary">
                      Просмотр
                    </Link>
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

