# Полный код выбора района на странице "Мои объекты"

## 1. Компонент Objects.tsx - полный код выбора района

```typescript
// frontend/src/pages/user/Objects.tsx

import axios from 'axios'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import type { RealtyObjectListItem, ObjectsListResponse, ApiErrorResponse } from '../../types/models'
import './Objects.css'

export default function UserObjects(): JSX.Element {
  // Состояние для фильтра района
  const [districtFilter, setDistrictFilter] = useState('')
  const [districts, setDistricts] = useState<string[]>([])
  
  // ... другие состояния ...
  const [objects, setObjects] = useState<RealtyObjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('creation_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [roomsTypeFilter, setRoomsTypeFilter] = useState('')

  // Загрузка списка районов при монтировании компонента
  useEffect(() => {
    void loadDistricts()
  }, [])

  // Автоматическая перезагрузка объектов при изменении любого фильтра
  useEffect(() => {
    void loadObjects()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, sortBy, sortOrder, roomsTypeFilter, districtFilter])

  // Функция загрузки районов из API
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

  // Функция загрузки объектов с учетом всех фильтров, включая район
  const loadObjects = async (): Promise<void> => {
    try {
      setLoading(true)
      const params: { 
        status?: string
        sort_by?: string
        sort_order?: string
        rooms_type?: string
        district?: string  // <-- Параметр фильтра района
      } = {}
      
      if (statusFilter) params.status = statusFilter
      if (sortBy) params.sort_by = sortBy
      if (sortOrder) params.sort_order = sortOrder
      if (roomsTypeFilter) params.rooms_type = roomsTypeFilter
      if (districtFilter) params.district = districtFilter  // <-- Передаем фильтр района в API
      
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
    <Layout title="Мои объекты" headerActions={...}>
      <div className="objects-page">
        <div className="card">
          <div className="card-header-row">
            <h2 className="card-title">Список объектов</h2>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              
              {/* SELECT ДЛЯ ВЫБОРА РАЙОНА */}
              <select
                className="form-input form-input-sm"
                value={districtFilter}
                onChange={(e) => setDistrictFilter(e.target.value)}  // <-- НЕМЕДЛЕННАЯ РЕАКЦИЯ
              >
                <option value="">Все районы</option>
                {districts.map((district) => (
                  <option key={district} value={district}>
                    {district}
                  </option>
                ))}
              </select>
              
              {/* ... другие select'ы ... */}
            </div>
          </div>
          
          {/* Отображение объектов */}
          {loading ? (
            <div className="loading">Загрузка...</div>
          ) : objects.length === 0 ? (
            <div className="empty-state">
              У вас пока нет объектов.
            </div>
          ) : (
            <div className="objects-list">
              {objects.map((obj) => (
                <div key={obj.object_id} className="object-card">
                  {/* ... карточка объекта ... */}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
```

## 2. Как это работает - пошагово:

### Шаг 1: Загрузка районов
```typescript
useEffect(() => {
  void loadDistricts()  // Загружаем список районов при монтировании
}, [])

const loadDistricts = async (): Promise<void> => {
  const res = await api.get<{ districts: string[] }>('/user/dashboard/districts')
  setDistricts(res.data.districts || [])  // Сохраняем в состояние
}
```

### Шаг 2: Пользователь выбирает район
```typescript
<select
  value={districtFilter}
  onChange={(e) => setDistrictFilter(e.target.value)}  // <-- СРАЗУ обновляет состояние
>
```

### Шаг 3: Автоматическая реакция на изменение
```typescript
useEffect(() => {
  void loadObjects()  // <-- АВТОМАТИЧЕСКИ вызывается при изменении districtFilter
}, [districtFilter])  // <-- Следит за изменением фильтра
```

### Шаг 4: Перезагрузка объектов с фильтром
```typescript
const loadObjects = async (): Promise<void> => {
  const params = {}
  if (districtFilter) params.district = districtFilter  // <-- Передаем в API
  const res = await api.get('/user/dashboard/objects/list', { params })
  setObjects(res.data.objects || [])  // <-- Обновляем список объектов
}
```

## 3. Ключевые моменты:

✅ **Немедленная реакция**: `onChange` срабатывает сразу при выборе  
✅ **Автоматическая перезагрузка**: через `useEffect`  
✅ **Простота**: обычный HTML `<select>` с `onChange`  
✅ **Типизация**: все типизировано через TypeScript  

## 4. Аналогия для нижних кнопок:

Точно так же работает для кнопок "Объекты" и "Меню навигации":

```typescript
// При клике на кнопку → открывается меню (как select открывается)
// При выборе опции → НЕМЕДЛЕННО применяется действие:
//   - Для навигации: navigate(path) → сразу переход на страницу
//   - Для объектов: navigate(`/objects/${id}`) → сразу открывается объект
```

## 5. CSS стили для select района:

```css
/* frontend/src/pages/user/Objects.css */
.form-input-sm {
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm);
  max-width: 200px;
}
```

