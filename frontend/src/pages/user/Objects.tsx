import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { FilterCard } from '../../components/FilterCard'
import { FilterSelect } from '../../components/FilterSelect'
import { useApiData } from '../../hooks/useApiData'
import api from '../../utils/api'
import { ROOMS_TYPES, OBJECT_STATUSES, OBJECT_SORT_OPTIONS } from '../../utils/constants'
import type { RealtyObjectListItem, ObjectsListResponse } from '../../types/models'
import './Objects.css'

export default function UserObjects(): JSX.Element {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('creation_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [roomsTypeFilter, setRoomsTypeFilter] = useState('')
  const [districtFilter, setDistrictFilter] = useState('')
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedObjects, setSelectedObjects] = useState<Set<number | string>>(new Set())

  // Загрузка районов
  const { data: districtsData } = useApiData<{ districts: string[] }>({
    url: '/user/dashboard/districts',
    errorContext: 'Loading districts',
    defaultErrorMessage: 'Ошибка загрузки районов',
  })
  const districts = districtsData?.districts || []

  // Загрузка настроек отображения
  const { data: settingsData } = useApiData<{ object_list_display_types?: string[] }>({
    url: '/user/dashboard/settings/data',
    errorContext: 'Loading settings',
    defaultErrorMessage: 'Ошибка загрузки настроек',
  })
  const listDisplayTypes = settingsData?.object_list_display_types || []

  // Загрузка объектов с фильтрами
  const { data: objectsData, loading } = useApiData<ObjectsListResponse>({
    url: '/user/dashboard/objects/list',
    params: {
      ...(statusFilter && { status: statusFilter }),
      ...(sortBy && { sort_by: sortBy }),
      ...(sortOrder && { sort_order: sortOrder }),
      ...(roomsTypeFilter && { rooms_type: roomsTypeFilter }),
      ...(districtFilter && { district: districtFilter }),
    },
    deps: [statusFilter, sortBy, sortOrder, roomsTypeFilter, districtFilter],
    errorContext: 'Loading objects',
    defaultErrorMessage: 'Ошибка загрузки объектов',
  })
  const objects = objectsData?.objects || []

  // Обработка изменения сортировки
  const handleSortChange = (value: string): void => {
    const lastUnderscoreIndex = value.lastIndexOf('_')
    if (lastUnderscoreIndex > 0 && lastUnderscoreIndex < value.length - 1) {
      const newSortBy = value.substring(0, lastUnderscoreIndex)
      const newSortOrder = value.substring(lastUnderscoreIndex + 1) as 'asc' | 'desc'
      if (newSortBy !== sortBy || newSortOrder !== sortOrder) {
        setSortBy(newSortBy)
        setSortOrder(newSortOrder)
      }
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
        <FilterCard
          headerActions={
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
          }
        >
          <FilterSelect
            value={statusFilter}
            onChange={setStatusFilter}
            options={OBJECT_STATUSES.map((status) => ({ value: status, label: status }))}
            placeholder="Все статусы"
            size="sm"
          />
          <FilterSelect
            value={roomsTypeFilter}
            onChange={setRoomsTypeFilter}
            options={ROOMS_TYPES.map((type) => ({ value: type, label: type }))}
            placeholder="Все типы комнат"
            size="sm"
          />
          <FilterSelect
            value={districtFilter}
            onChange={setDistrictFilter}
            options={districts.map((district) => ({ value: district, label: district }))}
            placeholder="Все районы"
            size="sm"
          />
          <FilterSelect
            value={`${sortBy}_${sortOrder}`}
            onChange={handleSortChange}
            options={OBJECT_SORT_OPTIONS.map((opt) => ({ value: opt.value, label: opt.label }))}
            placeholder=""
            size="sm"
          />
        </FilterCard>

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


