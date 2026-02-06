import { useEffect, useState } from 'react'
import axios from 'axios'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import type {
  AutopublishItem,
  AutopublishListResponse,
  RealtyObjectListItem,
  ApiErrorResponse,
} from '../../types/models'
import './Autopublish.css'

export default function Autopublish(): JSX.Element {
  const [items, setItems] = useState<AutopublishItem[]>([])
  const [availableObjects, setAvailableObjects] = useState<RealtyObjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    void loadData()
  }, [])

  const loadData = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<AutopublishListResponse>('/user/dashboard/autopublish')
      setItems(res.data.autopublish_items || [])
      setAvailableObjects(res.data.available_objects || [])
    } catch (err: unknown) {
      setError('Ошибка загрузки настроек автопубликации')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleAddObject = async (objectId: string): Promise<void> => {
    try {
      setSaving(true)
      setError('')
      const res = await api.post<{ success: boolean }>('/user/dashboard/autopublish', {
        object_id: objectId,
        bot_enabled: true,
      })
      if (res.data.success) {
        setSuccess('Объект добавлен в автопубликацию')
        setTimeout(() => setSuccess(''), 3000)
        await loadData()
      }
    } catch (err: unknown) {
      setError('Ошибка добавления объекта на автопубликацию')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setSaving(false)
    }
  }

  const handleToggleEnabled = async (objectId: string, enabled: boolean): Promise<void> => {
    try {
      setSaving(true)
      setError('')
      const res = await api.put<{ success: boolean }>(`/user/dashboard/autopublish/${objectId}`, {
        enabled: !enabled,
      })
      if (res.data.success) {
        await loadData()
      }
    } catch (err: unknown) {
      setError('Ошибка изменения настройки автопубликации')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (objectId: string): Promise<void> => {
    const confirmed = window.confirm('Убрать объект из автопубликации?')
    if (!confirmed) return

    try {
      setSaving(true)
      setError('')
      const res = await api.delete<{ success: boolean }>(`/user/dashboard/autopublish/${objectId}`)
      if (res.data.success) {
        setSuccess('Объект удален из автопубликации')
        setTimeout(() => setSuccess(''), 3000)
        await loadData()
      }
    } catch (err: unknown) {
      setError('Ошибка удаления объекта из автопубликации')
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error(err.response?.data || err.message)
      } else {
        console.error(err)
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Layout title="Автопубликация">
      <div className="autopublish-page">
        {error && (
          <div className="alert alert-error" onClick={() => setError('')}>
            {error}
          </div>
        )}
        {success && (
          <div className="alert alert-success" onClick={() => setSuccess('')}>
            {success}
          </div>
        )}

        <GlassCard className="autopublish-card">
          <div className="autopublish-header">
            <h2 className="card-title">Объекты на автопубликации</h2>
          </div>

          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : items.length === 0 ? (
            <div className="empty-state">
              <p>Нет объектов на автопубликации.</p>
            </div>
          ) : (
            <div className="autopublish-list">
              {items.map((item) => {
                const obj = item.object
                const cfg = item.config
                return (
                  <div key={obj.object_id} className="object-card compact autopublish-item">
                    <div className="object-details-compact single-line">
                      <span className="object-detail-item">{obj.object_id}</span>
                      {obj.rooms_type && <span className="object-detail-item">{obj.rooms_type}</span>}
                      {obj.price > 0 && <span className="object-detail-item">{obj.price}тр</span>}
                      {(obj.districts_json?.length || 0) > 0 && (
                        <span className="object-detail-item">
                          {(obj.districts_json || []).join(',')}
                        </span>
                      )}
                    </div>
                    <div className="autopublish-flags">
                      <span className={`badge ${cfg.enabled ? 'badge-success' : 'badge-secondary'}`}>
                        {cfg.enabled ? 'Включено' : 'Выключено'}
                      </span>
                      <span className="badge badge-secondary">
                        Бот: {cfg.bot_enabled ? 'да (по фильтрам чатов)' : 'нет'}
                      </span>
                    </div>
                    <div className="autopublish-actions">
                      <button
                        className="btn btn-small btn-secondary"
                        onClick={() => void handleToggleEnabled(obj.object_id as string, cfg.enabled)}
                        disabled={saving}
                      >
                        {cfg.enabled ? 'Выключить' : 'Включить'}
                      </button>
                      <button
                        className="btn btn-small btn-danger"
                        onClick={() => void handleDelete(obj.object_id as string)}
                        disabled={saving}
                      >
                        Убрать
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </GlassCard>

        <GlassCard className="autopublish-card">
          <h2 className="card-title">Добавить объект на автопубликацию</h2>
          {availableObjects.length === 0 ? (
            <div className="empty-state">
              <p>Нет доступных объектов (кроме архива), которые не в автопубликации.</p>
            </div>
          ) : (
            <div className="autopublish-available-list">
              {availableObjects.map((obj) => (
                <button
                  key={obj.object_id}
                  type="button"
                  className="object-card compact autopublish-available-item"
                  onClick={() => void handleAddObject(obj.object_id as string)}
                  disabled={saving}
                >
                  <div className="object-details-compact single-line">
                    <span className="object-detail-item">{obj.object_id}</span>
                    {obj.rooms_type && <span className="object-detail-item">{obj.rooms_type}</span>}
                    {obj.price > 0 && <span className="object-detail-item">{obj.price}тр</span>}
                    {(obj.districts_json?.length || 0) > 0 && (
                      <span className="object-detail-item">
                        {(obj.districts_json || []).join(',')}
                      </span>
                    )}
                  </div>
                  <span className="badge badge-primary">Добавить</span>
                </button>
              ))}
            </div>
          )}
        </GlassCard>
      </div>
    </Layout>
  )
}

