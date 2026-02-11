import axios from 'axios'
import { useEffect, useState, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import type { RealtyObject, PublishObjectRequest, PublishObjectResponse, ApiErrorResponse } from '../../types/models'
import './ViewObject.css'

export default function ViewObject(): JSX.Element {
  const { objectId } = useParams<{ objectId: string }>()
  const navigate = useNavigate()
  const [object, setObject] = useState<RealtyObject | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [publishError, setPublishError] = useState('')
  const [publishSuccess, setPublishSuccess] = useState(false)
  const [showAccountPublishModal, setShowAccountPublishModal] = useState(false)
  const [accounts, setAccounts] = useState<Array<{ account_id: number; phone: string }>>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [chats, setChats] = useState<Array<{ chat_id: number; title: string }>>([])
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null)
  const [publishingViaAccount, setPublishingViaAccount] = useState(false)

  const loadObject = useCallback(async () => {
    if (!objectId) return
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
  }, [objectId])

  useEffect(() => {
    void loadObject()
  }, [loadObject])

  const handlePublish = async (): Promise<void> => {
    if (!objectId) return

    if (!confirm('Вы уверены, что хотите опубликовать этот объект через бота?')) {
      return
    }

    try {
      setPublishing(true)
      setPublishError('')
      setPublishSuccess(false)

      const requestData: PublishObjectRequest = {
        object_id: objectId,
      }

      const res = await api.post<PublishObjectResponse>('/user/dashboard/objects/publish', requestData)

      if (res.data.success) {
        setPublishSuccess(true)
        // Reload object to get updated status
        await loadObject()
      } else {
        setPublishError(res.data.error || 'Ошибка публикации')
      }
    } catch (err: unknown) {
      let message = 'Ошибка публикации'
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        message = err.response?.data?.error || err.message || message
      }
      setPublishError(message)
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

  if (error) {
    return (
      <Layout title="Ошибка">
        <div className="view-object-page">
          <div className="alert alert-error">{error}</div>
          <Link to="/user/dashboard/objects" className="btn btn-primary">
            Вернуться к списку
          </Link>
        </div>
      </Layout>
    )
  }

  if (!object) {
    return (
      <Layout title="Объект не найден">
        <div className="view-object-page">
          <div className="alert alert-error">Объект не найден</div>
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

        <GlassCard>
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
            <button
              onClick={async () => {
                try {
                  const res = await api.get<Array<{ account_id: number; phone: string }>>('/accounts')
                  setAccounts(res.data.filter(acc => acc.is_active))
                  setShowAccountPublishModal(true)
                } catch (err) {
                  setPublishError('Ошибка загрузки аккаунтов')
                }
              }}
              className="btn btn-primary"
            >
              Опубликовать через аккаунт
            </button>
            <button
              onClick={handlePublish}
              disabled={publishing || !object.can_publish}
              className="btn btn-primary"
              title={!object.can_publish && object.last_publication ? 
                `Объект был опубликован менее 24 часов назад. Последняя публикация: ${new Date(object.last_publication).toLocaleString('ru-RU')}` : 
                undefined}
            >
              {publishing ? 'Публикация...' : 
               !object.can_publish ? 'Опубликовать (нельзя - прошло менее 24 часов)' :
               'Опубликовать через бота'}
            </button>
          </div>
        </GlassCard>
      </div>

      {showAccountPublishModal && (
        <div className="modal-overlay" onClick={() => setShowAccountPublishModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Опубликовать через аккаунт</h3>
              <button className="modal-close" onClick={() => setShowAccountPublishModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Выберите аккаунт:</label>
                <select
                  value={selectedAccountId || ''}
                  onChange={async (e) => {
                    const accId = Number(e.target.value)
                    setSelectedAccountId(accId)
                    setSelectedChatId(null)
                    try {
                      const res = await api.get<Array<{ chat_id: number; title: string }>>('/chats', {
                        params: { account_id: accId, owner_type: 'user' }
                      })
                      setChats(res.data)
                    } catch (err) {
                      setPublishError('Ошибка загрузки чатов')
                    }
                  }}
                  className="form-control"
                >
                  <option value="">Выберите аккаунт</option>
                  {accounts.map(acc => (
                    <option key={acc.account_id} value={acc.account_id}>
                      {acc.phone}
                    </option>
                  ))}
                </select>
              </div>
              {selectedAccountId && (
                <div className="form-group">
                  <label>Выберите чат:</label>
                  <select
                    value={selectedChatId || ''}
                    onChange={(e) => setSelectedChatId(Number(e.target.value))}
                    className="form-control"
                  >
                    <option value="">Выберите чат</option>
                    {chats.map(chat => (
                      <option key={chat.chat_id} value={chat.chat_id}>
                        {chat.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="modal-actions">
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowAccountPublishModal(false)}
                >
                  Отмена
                </button>
                <button
                  className="btn btn-primary"
                  onClick={async () => {
                    if (!objectId || !selectedAccountId || !selectedChatId) return
                    try {
                      setPublishingViaAccount(true)
                      setPublishError('')
                      const res = await api.post<{ success: boolean; message_id?: number }>('/objects/publish-via-account', {
                        object_id: objectId,
                        account_id: selectedAccountId,
                        chat_id: selectedChatId
                      })
                      if (res.data.success) {
                        setPublishSuccess(true)
                        setShowAccountPublishModal(false)
                        await loadObject()
                      }
                    } catch (err: unknown) {
                      if (axios.isAxiosError<ApiErrorResponse>(err)) {
                        setPublishError(err.response?.data?.error || 'Ошибка публикации')
                      } else {
                        setPublishError('Ошибка публикации')
                      }
                    } finally {
                      setPublishingViaAccount(false)
                    }
                  }}
                  disabled={!selectedAccountId || !selectedChatId || publishingViaAccount}
                >
                  {publishingViaAccount ? 'Публикация...' : 'Опубликовать'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}

