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
  const [previewing, setPreviewing] = useState(false)
  const [previewError, setPreviewError] = useState('')
  const [previewSuccess, setPreviewSuccess] = useState(false)
  const [autopublishEnabled, setAutopublishEnabled] = useState(false)
  const [publicationFormat, setPublicationFormat] = useState<'default' | 'compact'>('default')
  const [loadingAutopublish, setLoadingAutopublish] = useState(false)
  const [autopublishError, setAutopublishError] = useState('')
  const [objectChats, setObjectChats] = useState<{
    user_chats?: Array<{ chat_id: number; title: string; category?: string }>
    chat_groups?: Array<{ group_id: number; name: string; category?: string; chats?: Array<{ chat_id: number; title: string }> }>
  } | null>(null)
  const [loadingObjectChats, setLoadingObjectChats] = useState(false)

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

  // Загрузка чатов и групп для объекта
  useEffect(() => {
    if (!objectId) return
    void (async () => {
      try {
        setLoadingObjectChats(true)
        const res = await api.get<{
          user_chats?: Array<{ chat_id: number; title: string; category?: string }>
          chat_groups?: Array<{ group_id: number; name: string; category?: string; chats?: Array<{ chat_id: number; title: string }> }>
        }>(`/user/dashboard/autopublish/${objectId}/chats`)
        setObjectChats(res.data)
      } catch (err) {
        console.error('Error loading object chats:', err)
      } finally {
        setLoadingObjectChats(false)
      }
    })()
  }, [objectId])

  // Загрузка настроек автопубликации
  useEffect(() => {
    if (!objectId) return
    void (async () => {
      try {
        const res = await api.get<{
          enabled: boolean
          bot_enabled: boolean
          accounts_config_json?: {
            publication_format?: 'default' | 'compact'
            accounts?: Array<{ account_id: number; chat_ids: number[] }>
          }
        }>(`/user/dashboard/autopublish/${objectId}`)
        if (res.data) {
          setAutopublishEnabled(res.data.enabled || false)
          setPublicationFormat(res.data.accounts_config_json?.publication_format || 'default')
        }
      } catch (err) {
        // Игнорируем ошибку если конфиг не найден - это нормально
        console.log('Autopublish config not found, using defaults')
      }
    })()
  }, [objectId])

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
        {previewError && <div className="alert alert-error">{previewError}</div>}
        {previewSuccess && (
          <div className="alert alert-success">
            Превью отправлено в Telegram! Проверьте бота.
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

            {object.residential_complex && (
              <div className="detail-item detail-item-full">
                <label>ЖК</label>
                <div className="detail-value">{object.residential_complex}</div>
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

            {(object.contact_name || object.phone_number || object.contact_name_2 || object.phone_number_2) && (
              <div className="detail-item detail-item-full">
                <label>Контакты</label>
                <div className="detail-value">
                  {object.contact_name && <div>{object.contact_name}</div>}
                  {object.phone_number && <div>{object.phone_number}</div>}
                  {(object.contact_name_2 || object.phone_number_2) && (
                    <>
                      {object.contact_name_2 && <div>{object.contact_name_2}</div>}
                      {object.phone_number_2 && <div>{object.phone_number_2}</div>}
                    </>
                  )}
                  {object.show_username && <div>Показывать username в Telegram</div>}
                </div>
              </div>
            )}

            {object.photos_json && object.photos_json.length > 0 && (
              <div className="detail-item detail-item-full">
                <label>Фотографии</label>
                <div className="photos-grid">
                  {object.photos_json.map((photo, idx) => {
                    // Обработка фото: может быть строкой (путь) или объектом (dict с file_id или path)
                    let photoUrl = ''
                    if (typeof photo === 'string') {
                      // Если это строка - путь к файлу
                      photoUrl = `/${photo}`
                    } else if (photo && typeof photo === 'object') {
                      // Если это объект - извлекаем путь или file_id
                      photoUrl = photo.path || photo.file_id || ''
                      if (photoUrl && !photoUrl.startsWith('/') && !photoUrl.startsWith('http')) {
                        photoUrl = `/${photoUrl}`
                      }
                    }
                    
                    if (!photoUrl) return null
                    
                    return (
                      <img
                        key={idx}
                        src={photoUrl}
                        alt={`Фото ${idx + 1}`}
                        className="object-photo"
                        onError={(e) => {
                          // Если загрузка не удалась, скрываем изображение
                          e.currentTarget.style.display = 'none'
                        }}
                      />
                    )
                  })}
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

          <div className="autopublish-settings" style={{ marginTop: '20px', padding: '15px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}>
            <h3 style={{ marginTop: 0, marginBottom: '15px', fontSize: '16px' }}>Настройки автопубликации</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="checkbox"
                  id="autopublish-enabled"
                  checked={autopublishEnabled}
                  onChange={async (e) => {
                    const enabled = e.target.checked
                    setLoadingAutopublish(true)
                    setAutopublishError('')
                    try {
                      if (enabled) {
                        // Включаем автопубликацию
                        await api.post('/user/dashboard/autopublish', {
                          object_id: objectId,
                          bot_enabled: true,
                          accounts_config_json: {
                            publication_format: publicationFormat,
                            accounts: []
                          }
                        })
                      } else {
                        // Выключаем автопубликацию
                        await api.delete(`/user/dashboard/autopublish/${objectId}`)
                      }
                      setAutopublishEnabled(enabled)
                    } catch (err: unknown) {
                      let message = 'Ошибка изменения настроек автопубликации'
                      if (axios.isAxiosError<ApiErrorResponse>(err)) {
                        message = err.response?.data?.error || message
                      }
                      setAutopublishError(message)
                    } finally {
                      setLoadingAutopublish(false)
                    }
                  }}
                  disabled={loadingAutopublish}
                />
                <label htmlFor="autopublish-enabled" style={{ cursor: 'pointer' }}>
                  Включить автопубликацию
                </label>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <label htmlFor="publication-format" style={{ minWidth: '150px', flexShrink: 0 }}>
                  Формат публикации:
                </label>
                <select
                  id="publication-format"
                  value={publicationFormat}
                  onChange={async (e) => {
                    const format = e.target.value as 'default' | 'compact'
                    setLoadingAutopublish(true)
                    setAutopublishError('')
                    try {
                      if (autopublishEnabled) {
                        await api.put(`/user/dashboard/autopublish/${objectId}`, {
                          bot_enabled: true,
                          accounts_config_json: {
                            publication_format: format,
                            accounts: []
                          }
                        })
                      } else {
                        // Если автопубликация выключена, просто сохраняем формат для будущего использования
                        await api.post('/user/dashboard/autopublish', {
                          object_id: objectId,
                          bot_enabled: false,
                          accounts_config_json: {
                            publication_format: format,
                            accounts: []
                          }
                        })
                      }
                      setPublicationFormat(format)
                    } catch (err: unknown) {
                      let message = 'Ошибка изменения формата публикации'
                      if (axios.isAxiosError<ApiErrorResponse>(err)) {
                        message = err.response?.data?.error || message
                      }
                      setAutopublishError(message)
                    } finally {
                      setLoadingAutopublish(false)
                    }
                  }}
                  disabled={loadingAutopublish}
                  style={{ 
                    padding: '8px', 
                    borderRadius: '4px', 
                    border: '1px solid rgba(255,255,255,0.2)', 
                    background: 'rgba(255,255,255,0.05)', 
                    color: 'inherit',
                    minWidth: '150px',
                    maxWidth: '100%',
                    flex: '1 1 auto'
                  }}
                >
                  <option value="default">Стандартный</option>
                  <option value="compact">Компактный</option>
                </select>
              </div>
              {autopublishError && (
                <div className="alert alert-error" style={{ marginTop: '10px', fontSize: '14px' }}>
                  {autopublishError}
                </div>
              )}
            </div>
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
                  setPreviewing(true)
                  setPreviewError('')
                  setPreviewSuccess(false)
                  const res = await api.post<{ success: boolean; message?: string }>(`/user/dashboard/objects/${objectId}/preview`)
                  if (res.data.success) {
                    setPreviewSuccess(true)
                    setTimeout(() => setPreviewSuccess(false), 5000)
                  }
                } catch (err: unknown) {
                  let message = 'Ошибка отправки превью'
                  if (axios.isAxiosError<ApiErrorResponse>(err)) {
                    message = err.response?.data?.error || err.response?.data?.details || err.message || message
                  }
                  setPreviewError(message)
                  setTimeout(() => setPreviewError(''), 5000)
                } finally {
                  setPreviewing(false)
                }
              }}
              disabled={previewing}
              className="btn btn-secondary"
            >
              {previewing ? 'Отправка...' : 'Превью в боте'}
            </button>
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

          {/* Отображение чатов и групп (блок всегда виден, даже если чатов нет) */}
          <div
            style={{
              marginTop: '20px',
              padding: '15px',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
            }}
          >
            <h3 style={{ marginTop: 0, marginBottom: '10px', fontSize: '16px' }}>Привязанные чаты и группы</h3>

            {loadingObjectChats && (
              <div className="loading" style={{ fontSize: '13px' }}>
                Загрузка списка чатов...
              </div>
            )}

            {!loadingObjectChats &&
              (!objectChats ||
                (((objectChats.user_chats?.length || 0) === 0) &&
                  ((objectChats.chat_groups?.length || 0) === 0))) && (
                <div style={{ fontSize: '13px', opacity: 0.7 }}>
                  Для этого объекта пока не настроены чаты и группы автопубликации.
                </div>
              )}

            {objectChats && (objectChats.user_chats?.length || 0) > 0 && (
              <div style={{ marginTop: '10px', marginBottom: '10px' }}>
                <strong style={{ fontSize: '14px', display: 'block', marginBottom: '8px' }}>Аккаунт-чаты:</strong>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {objectChats.user_chats!.map((chat) => (
                    <span
                      key={chat.chat_id}
                      style={{
                        padding: '4px 8px',
                        background: 'rgba(255, 255, 255, 0.1)',
                        borderRadius: '4px',
                        fontSize: '13px',
                      }}
                    >
                      {chat.title}
                      {chat.category && ` (${chat.category})`}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {objectChats && (objectChats.chat_groups?.length || 0) > 0 && (
              <div style={{ marginTop: (objectChats.user_chats?.length || 0) > 0 ? '5px' : '10px' }}>
                <strong style={{ fontSize: '14px', display: 'block', marginBottom: '8px' }}>Группы чатов:</strong>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {objectChats.chat_groups!.map((group) => (
                    <div
                      key={group.group_id}
                      style={{
                        padding: '8px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '4px',
                      }}
                    >
                      <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                        {group.name}
                        {group.category && ` (${group.category})`}
                      </div>
                      {group.chats && group.chats.length > 0 && (
                        <div
                          style={{
                            fontSize: '12px',
                            color: 'rgba(255, 255, 255, 0.7)',
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: '4px',
                          }}
                        >
                          {group.chats.map((chat) => (
                            <span key={chat.chat_id}>{chat.title}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
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

