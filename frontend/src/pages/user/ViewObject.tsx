import axios from 'axios'
import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import './ViewObject.css'

interface RealtyObject {
  object_id: string
  status: string
  rooms_type?: string | null
  price: number
  area?: number | null
  floor?: string | null
  districts_json?: string[] | null
  comment?: string | null
  address?: string | null
  renovation?: string | null
  contact_name?: string | null
  phone_number?: string | null
  show_username?: boolean
  photos_json?: string[] | null
  creation_date?: string
  publication_date?: string
}

export default function ViewObject(): JSX.Element {
  const { objectId } = useParams<{ objectId: string }>()
  const navigate = useNavigate()
  const [object, setObject] = useState<RealtyObject | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [publishError, setPublishError] = useState('')
  const [publishSuccess, setPublishSuccess] = useState(false)

  useEffect(() => {
    if (objectId) {
      void loadObject()
    }
  }, [objectId])

  const loadObject = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<RealtyObject>(`/user/dashboard/objects/${objectId}`)
      setObject(res.data)
    } catch (err: unknown) {
      setError('Ошибка загрузки объекта')
      if (axios.isAxiosError(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    if (!objectId) return

    if (!confirm('Вы уверены, что хотите опубликовать этот объект через бота?')) {
      return
    }

    try {
      setPublishing(true)
      setPublishError('')
      setPublishSuccess(false)

      const res = await api.post('/user/dashboard/objects/publish', {
        object_id: objectId
      })

      if (res.data.success) {
        setPublishSuccess(true)
        // Reload object to get updated status
        await loadObject()
      } else {
        setPublishError(res.data.error || 'Ошибка публикации')
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setPublishError(err.response?.data?.error || 'Ошибка публикации')
      } else {
        setPublishError('Ошибка публикации')
      }
    } finally {
      setPublishing(false)
    }
  }

  if (loading) {
    return (
      <Layout title="Просмотр объекта">
        <div className="view-object-page">
          <div className="loading">Загрузка...</div>
        </div>
      </Layout>
    )
  }

  if (error || !object) {
    return (
      <Layout title="Ошибка">
        <div className="view-object-page">
          <div className="alert alert-error">{error || 'Объект не найден'}</div>
          <Link to="/user/dashboard/objects" className="btn btn-primary">
            Вернуться к списку
          </Link>
        </div>
      </Layout>
    )
  }

  return (
    <Layout
      title={`Объект ${object.object_id}`}
      headerActions={
        <Link to="/user/dashboard/objects" className="header-icon-btn">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path
              d="M12.5 15L7.5 10L12.5 5"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </Link>
      }
    >
      <div className="view-object-page">
        {publishError && <div className="alert alert-error">{publishError}</div>}
        {publishSuccess && (
          <div className="alert alert-success">
            Объект успешно опубликован через бота! Проверьте Telegram для подтверждения.
          </div>
        )}

        <div className="card">
          <div className="card-header-row">
            <h2 className="card-title">Информация об объекте</h2>
            <span
              className={`badge badge-${
                object.status === 'опубликовано'
                  ? 'success'
                  : object.status === 'черновик'
                    ? 'warning'
                    : 'secondary'
              }`}
            >
              {object.status}
            </span>
          </div>

          <div className="object-details-grid">
            <div className="detail-item">
              <label>ID объекта</label>
              <div className="detail-value">{object.object_id}</div>
            </div>

            {object.rooms_type && (
              <div className="detail-item">
                <label>Тип комнат</label>
                <div className="detail-value">{object.rooms_type}</div>
              </div>
            )}

            {object.price > 0 && (
              <div className="detail-item">
                <label>Цена</label>
                <div className="detail-value">{object.price} тыс. руб.</div>
              </div>
            )}

            {object.area && (
              <div className="detail-item">
                <label>Площадь</label>
                <div className="detail-value">{object.area} м²</div>
              </div>
            )}

            {object.floor && (
              <div className="detail-item">
                <label>Этаж</label>
                <div className="detail-value">{object.floor}</div>
              </div>
            )}

            {object.renovation && (
              <div className="detail-item">
                <label>Ремонт</label>
                <div className="detail-value">{object.renovation}</div>
              </div>
            )}

            {object.address && (
              <div className="detail-item detail-item-full">
                <label>Адрес</label>
                <div className="detail-value">{object.address}</div>
              </div>
            )}

            {(object.districts_json?.length || 0) > 0 && (
              <div className="detail-item detail-item-full">
                <label>Районы</label>
                <div className="detail-value">{(object.districts_json || []).join(', ')}</div>
              </div>
            )}

            {object.comment && (
              <div className="detail-item detail-item-full">
                <label>Комментарий</label>
                <div className="detail-value">{object.comment}</div>
              </div>
            )}

            {(object.contact_name || object.phone_number) && (
              <div className="detail-item detail-item-full">
                <label>Контакты</label>
                <div className="detail-value">
                  {object.contact_name && <div>{object.contact_name}</div>}
                  {object.phone_number && <div>{object.phone_number}</div>}
                  {object.show_username && <div>Показывать username в Telegram</div>}
                </div>
              </div>
            )}

            {object.photos_json && object.photos_json.length > 0 && (
              <div className="detail-item detail-item-full">
                <label>Фотографии</label>
                <div className="photos-grid">
                  {object.photos_json.map((photo, idx) => (
                    <img
                      key={idx}
                      src={`/${photo}`}
                      alt={`Фото ${idx + 1}`}
                      className="object-photo"
                    />
                  ))}
                </div>
              </div>
            )}

            {object.creation_date && (
              <div className="detail-item">
                <label>Дата создания</label>
                <div className="detail-value">
                  {new Date(object.creation_date).toLocaleString('ru-RU')}
                </div>
              </div>
            )}

            {object.publication_date && (
              <div className="detail-item">
                <label>Дата публикации</label>
                <div className="detail-value">
                  {new Date(object.publication_date).toLocaleString('ru-RU')}
                </div>
              </div>
            )}
          </div>

          <div className="object-actions">
            <Link
              to={`/user/dashboard/objects/${object.object_id}/edit`}
              className="btn btn-secondary"
            >
              Редактировать
            </Link>
            {object.status !== 'опубликовано' && (
              <button
                onClick={handlePublish}
                disabled={publishing}
                className="btn btn-primary"
              >
                {publishing ? 'Публикация...' : 'Опубликовать через бота'}
              </button>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}

