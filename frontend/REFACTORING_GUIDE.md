# Руководство по рефакторингу Frontend

## Созданные переиспользуемые элементы

### 1. Константы (`utils/constants.ts`)
**Цель**: Единый источник истины для всех перечислений

- `ROOMS_TYPES` - типы комнат
- `RENOVATION_TYPES` - типы ремонта
- `OBJECT_STATUSES` - статусы объектов
- `OBJECT_SORT_OPTIONS` - опции сортировки
- `PHONE_PATTERN` - паттерн валидации телефона
- `PHONE_ERROR_MESSAGE` - сообщение об ошибке телефона

**Использование**:
```typescript
import { ROOMS_TYPES, OBJECT_STATUSES, PHONE_PATTERN } from '../../utils/constants'
```

### 2. Обработка ошибок (`utils/errorHandler.ts`)
**Цель**: Единый способ обработки ошибок API

- `getErrorMessage()` - извлечение сообщения об ошибке
- `logError()` - логирование ошибок
- `isAuthError()` - проверка ошибки авторизации

**Использование**:
```typescript
import { getErrorMessage, logError } from '../../utils/errorHandler'

try {
  // ...
} catch (err: unknown) {
  const message = getErrorMessage(err, 'Ошибка по умолчанию')
  logError(err, 'Context')
}
```

### 3. Хуки для работы с API

#### `useApiData` (`hooks/useApiData.ts`)
**Цель**: Единый паттерн загрузки данных

**Использование**:
```typescript
import { useApiData } from '../../hooks/useApiData'

const { data, loading, error, reload } = useApiData<ResponseType>({
  url: '/api/endpoint',
  params: { filter: 'value' },
  deps: [dependency1, dependency2], // для перезагрузки
  errorContext: 'Loading data',
  defaultErrorMessage: 'Ошибка загрузки',
})
```

#### `useApiMutation` (`hooks/useApiMutation.ts`)
**Цель**: Единый паттерн для мутаций (создание, обновление, удаление)

**Использование**:
```typescript
import { useApiMutation } from '../../hooks/useApiMutation'

const { mutate, loading, error, clearError } = useApiMutation<RequestType, ResponseType>({
  url: '/api/endpoint',
  method: 'POST',
  onSuccess: (data) => {
    // обработка успеха
  },
  onError: (error) => {
    // обработка ошибки
  },
})

await mutate(requestData)
```

### 4. Компоненты фильтров

#### `FilterSelect` (`components/FilterSelect.tsx`)
**Цель**: Единый стиль для всех фильтров-селектов

**Использование**:
```typescript
import { FilterSelect } from '../../components/FilterSelect'

<FilterSelect
  value={filterValue}
  onChange={setFilterValue}
  options={[
    { value: 'option1', label: 'Опция 1' },
    { value: 'option2', label: 'Опция 2' },
  ]}
  placeholder="Все"
  size="sm"
/>
```

#### `FilterCard` (`components/FilterCard.tsx`)
**Цель**: Единый стиль для блоков фильтров

**Использование**:
```typescript
import { FilterCard } from '../../components/FilterCard'

<FilterCard
  title="Фильтры"
  headerActions={<button>Действие</button>}
>
  <FilterSelect ... />
  <FilterSelect ... />
</FilterCard>
```

## Примеры рефакторинга

### До рефакторинга (Objects.tsx)
```typescript
const [objects, setObjects] = useState<RealtyObjectListItem[]>([])
const [loading, setLoading] = useState(true)
const [districts, setDistricts] = useState<string[]>([])

useEffect(() => {
  void loadDistricts()
}, [])

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
```

### После рефакторинга
```typescript
const { data: districtsData } = useApiData<{ districts: string[] }>({
  url: '/user/dashboard/districts',
  errorContext: 'Loading districts',
  defaultErrorMessage: 'Ошибка загрузки районов',
})
const districts = districtsData?.districts || []
```

## Применение к остальным страницам

### Chats.tsx
Заменить:
- `useState` + `useEffect` + `loadAccounts()` → `useApiData`
- `axios.isAxiosError` → `getErrorMessage`, `logError`
- Ручные селекты → `FilterSelect`

### TelegramAccounts.tsx
Заменить:
- `useState` + `useEffect` + `loadAccounts()` → `useApiData`
- `axios.isAxiosError` → `getErrorMessage`, `logError`
- Ручные обработки ошибок → единые утилиты

### Autopublish.tsx
Заменить:
- `useState` + `useEffect` + `loadData()` → `useApiData`
- `useState` + `useEffect` + `loadAccounts()` → `useApiData`
- Мутации → `useApiMutation`
- Обработка ошибок → `getErrorMessage`, `logError`

### Settings.tsx
Заменить:
- Загрузка данных → `useApiData`
- Сохранение → `useApiMutation`
- Валидация телефона → `PHONE_PATTERN`, `PHONE_ERROR_MESSAGE`

## Типизация

Все типы должны импортироваться из `types/models.ts`:
```typescript
import type { RealtyObjectListItem, ApiErrorResponse } from '../../types/models'
```

Типы из констант импортируются из `utils/constants.ts`:
```typescript
import type { RoomsType, ObjectStatus } from '../../utils/constants'
```

## Принципы рефакторинга

1. **Один источник истины**: Все константы в `utils/constants.ts`
2. **Переиспользование**: Использовать хуки и компоненты вместо дублирования
3. **Единая обработка ошибок**: Всегда использовать `getErrorMessage` и `logError`
4. **Типизация**: Строгая типизация всех данных
5. **Простота**: Простая логика, понятная нейросети

