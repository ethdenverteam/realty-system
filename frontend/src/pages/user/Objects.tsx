import axios from 'axios'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import type { RealtyObjectListItem, ObjectsListResponse, ApiErrorResponse } from '../../types/models'
import './Objects.css'

export default function UserObjects(): JSX.Element {
  const navigate = useNavigate()
  const [objects, setObjects] = useState<RealtyObjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('creation_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [roomsTypeFilter, setRoomsTypeFilter] = useState('')
  const [districtFilter, setDistrictFilter] = useState('')
  const [districts, setDistricts] = useState<string[]>([])
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedObjects, setSelectedObjects] = useState<Set<number | string>>(new Set())
  const [listDisplayTypes, setListDisplayTypes] = useState<string[]>([])

  useEffect(() => {
    void loadDistricts()
    void loadSettings()
  }, [])

  const loadSettings = async (): Promise<void> => {
    try {
      const res = await api.get<{ object_list_display_types?: string[] }>('/user/dashboard/settings/data')
      setListDisplayTypes(res.data.object_list_display_types || [])
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        console.error('Error loading settings:', err.response?.data || err.message)
      }
    }
  }

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
        {/* Фильтры в отдельном стеклянном блоке */}
        <GlassCard className="filters-card">
          <div className="filters-header">
            <h2 className="filters-title">Фильтры</h2>
            <button
              type="button"
              className={`selection-toggle ${selectionMode ? 'active' : ''}`}
              onClick={() => {
                setSelectionMode(!selectionMode)
                if (!selectionMode) {
                  setSelectedObjects(new Set())
                }
              }}
            >
              {selectionMode ? 'Отменить выбор' : 'Выбрать'}
            </button>
          </div>
          <div className="filters-row">
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
                <option value="евро1к">евро1к</option>
                <option value="евро2к">евро2к</option>
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
        </GlassCard>

        {/* Список объектов в отдельном блоке */}
        {loading ? (
            <div className="loading">Загрузка...</div>
          ) : objects.length === 0 ? (
            <GlassCard className="empty-state-card">
              <div className="empty-state">
                У вас пока нет объектов. <Link to="/user/dashboard/objects/create">Создайте первый объект</Link>
              </div>
            </GlassCard>
          ) : (
            <div className="objects-list">
              {objects
                .filter((obj) => {
                  // Фильтрация по настройкам отображения
                  if (listDisplayTypes.length > 0 && obj.rooms_type) {
                    return listDisplayTypes.includes(obj.rooms_type)
                  }
                  return true
                })
                .map((obj) => {
                  const isSelected = selectedObjects.has(obj.object_id)
                  return (
                    <div 
                      key={obj.object_id} 
                      className={`object-card compact ${isSelected ? 'selected' : ''}`}
                      onClick={(e) => {
                        if (selectionMode) {
                          e.preventDefault()
                          e.stopPropagation()
                          const newSelected = new Set(selectedObjects)
                          if (isSelected) {
                            newSelected.delete(obj.object_id)
                          } else {
                            newSelected.add(obj.object_id)
                          }
                          setSelectedObjects(newSelected)
                        } else {
                          navigate(`/user/dashboard/objects/${obj.object_id}`)
                        }
                      }}
                    >
                      <div className="object-details-compact single-line">
                        {obj.rooms_type && (
                          <span className="object-detail-item">
                            {obj.rooms_type}
                          </span>
                        )}
                        {obj.price > 0 && (
                          <span className="object-detail-item">
                            {obj.price}тр
                          </span>
                        )}
                        {obj.area && (
                          <span className="object-detail-item">
                            {obj.area}м²
                          </span>
                        )}
                        {(obj.districts_json?.length || 0) > 0 && (
                          <span className="object-detail-item">
                            {(obj.districts_json || []).join(',')}
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
            </div>
          )}
      </div>
    </Layout>
  )
}


