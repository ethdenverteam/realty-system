import { useState } from 'react'
import { observer } from 'mobx-react-lite'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import BottomNavDropdown, { createNavigationOptions, createObjectOptions } from '../../components/BottomNavDropdown'
import Dropdown, { type DropdownOption } from '../../components/Dropdown'
import { GlassCard } from '../../components/GlassCard'
import { GlassButton } from '../../components/GlassButton'
import GlassMenuButton from '../../components/GlassMenuButton'
import GlassSelectKeyWithIcon, { type GlassSelectOption } from '../../components/GlassSelectKeyWithIcon'
import { uiStore } from '../../stores/uiStore'
import type { RealtyObjectListItem } from '../../types/models'
import './DropdownTest.css'

/**
 * Тестовая страница для проверки работы выпадающих меню и кнопок
 * Демонстрирует различные варианты использования компонентов Dropdown, BottomNavDropdown и стеклянных кнопок
 */
function DropdownTest(): JSX.Element {
  const navigate = useNavigate()
  const [selectedValue1, setSelectedValue1] = useState<string | number>('')
  const [selectedValue2, setSelectedValue2] = useState<string | number>('')
  const [selectedValue3, setSelectedValue3] = useState<string | number>('')
  const [log, setLog] = useState<string[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [buttonStatusFilter, setButtonStatusFilter] = useState<string>('')
  const [testSelectValue, setTestSelectValue] = useState<string | number>('')

  // Тестовые данные для объектов
  const testObjects: RealtyObjectListItem[] = [
    { object_id: 1, rooms_type: 'Студия', price: 1000, status: 'черновик' },
    { object_id: 2, rooms_type: '1к', price: 1500, status: 'опубликовано' },
    { object_id: 3, rooms_type: '2к', price: 2000, status: 'черновик' },
    { object_id: 4, rooms_type: '3к', price: 3000, status: 'архив' },
  ]

  // Вариант 1: Простой выбор (как выбор района)
  const simpleOptions: DropdownOption[] = [
    { label: 'Все районы', value: '' },
    { label: 'Центральный', value: 'Центральный' },
    { label: 'Северный', value: 'Северный' },
    { label: 'Южный', value: 'Южный' },
    { label: 'Восточный', value: 'Восточный' },
    { label: 'Западный', value: 'Западный' },
  ]

  // Вариант 2: Навигация с иконками
  const navOptions = createNavigationOptions()

  // Вариант 3: Объекты из БД
  const objectOptions = createObjectOptions(testObjects)

  // Вариант 4: С отключенными опциями
  const disabledOptions: DropdownOption[] = [
    { label: 'Доступная опция 1', value: 'opt1' },
    { label: 'Отключенная опция', value: 'opt2', disabled: true },
    { label: 'Доступная опция 2', value: 'opt3' },
    { label: 'Отключенная опция 2', value: 'opt4', disabled: true },
  ]

  // Обработчики с логированием
  const handleSimpleSelect = (value: string | number): void => {
    setSelectedValue1(value)
    addLog(`Выбран район: ${value || 'Все районы'}`)
  }

  const handleNavSelect = (value: string | number): void => {
    setSelectedValue2(value)
    addLog(`Навигация: ${value}`)
    navigate(String(value))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleObjectSelect = (value: string | number): void => {
    setSelectedValue3(value)
    addLog(`Выбран объект: ${value}`)
    navigate(`/user/dashboard/objects/${value}`)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const addLog = (message: string): void => {
    const timestamp = new Date().toLocaleTimeString('ru-RU')
    setLog((prev) => [`[${timestamp}] ${message}`, ...prev].slice(0, 10))
  }

  return (
    <Layout title="Тест выпадающих меню и кнопок" isAdmin>
      <div className="dropdown-test-page">
        <div className="test-section">
          <h2>Документация: Выбор района</h2>
          <div className="documentation-box">
            <p>
              <strong>Как работает выбор района на странице "Мои объекты":</strong>
            </p>
            <ul>
              <li>
                <strong>Немедленная реакция:</strong> При выборе в select срабатывает onChange, который сразу обновляет состояние
              </li>
              <li>
                <strong>Автоматическая перезагрузка:</strong> useEffect следит за изменением фильтра и автоматически перезагружает объекты
              </li>
              <li>
                <strong>Простота:</strong> Обычный HTML select с onChange обработчиком
              </li>
            </ul>
            <pre className="code-block">
{`<select
  value={districtFilter}
  onChange={(e) => setDistrictFilter(e.target.value)}  // ← НЕМЕДЛЕННО
>
  <option value="">Все районы</option>
  {districts.map((district) => (
    <option key={district} value={district}>
      {district}
    </option>
  ))}
</select>`}
            </pre>
            <div className="full-code-section">
              <details>
                <summary style={{ cursor: 'pointer', fontWeight: 'bold', marginTop: 'var(--spacing-md)' }}>
                  Полный код выбора района (DISTRICT_SELECT_FULL_CODE.md)
                </summary>
                <div style={{ marginTop: 'var(--spacing-md)' }}>
                  <h4>1. Компонент Objects.tsx - полный код выбора района</h4>
                  <pre className="code-block">
{`// frontend/src/pages/user/Objects.tsx

// Состояние для фильтра района
const [districtFilter, setDistrictFilter] = useState('')
const [districts, setDistricts] = useState<string[]>([])

// Загрузка списка районов при монтировании компонента
useEffect(() => {
  void loadDistricts()
}, [])

// Автоматическая перезагрузка объектов при изменении любого фильтра
useEffect(() => {
  void loadObjects()
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

// SELECT ДЛЯ ВЫБОРА РАЙОНА
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
</select>`}
                  </pre>
                  
                  <h4>2. Как это работает - пошагово:</h4>
                  <ul>
                    <li><strong>Шаг 1:</strong> Загрузка районов при монтировании через useEffect</li>
                    <li><strong>Шаг 2:</strong> Пользователь выбирает район в select</li>
                    <li><strong>Шаг 3:</strong> onChange срабатывает СРАЗУ и обновляет districtFilter</li>
                    <li><strong>Шаг 4:</strong> useEffect автоматически вызывает loadObjects() при изменении districtFilter</li>
                    <li><strong>Шаг 5:</strong> Объекты перезагружаются с новым фильтром района</li>
                  </ul>
                  
                  <h4>3. Ключевые моменты:</h4>
                  <ul>
                    <li>✅ <strong>Немедленная реакция:</strong> onChange срабатывает сразу при выборе</li>
                    <li>✅ <strong>Автоматическая перезагрузка:</strong> через useEffect</li>
                    <li>✅ <strong>Простота:</strong> обычный HTML select с onChange</li>
                    <li>✅ <strong>Типизация:</strong> все типизировано через TypeScript</li>
                  </ul>
                </div>
              </details>
            </div>
          </div>
        </div>

        <div className="test-section">
          <h2>Фильтр статуса (как на странице &quot;Мои объекты&quot;)</h2>
          <p>Обычный HTML select с теми же классами и опциями, что и в проде.</p>
          <div className="test-controls">
            <select
              className="form-input form-input-sm"
              value={statusFilter}
              onChange={(e) => {
                const value = e.target.value
                setStatusFilter(value)
                addLog(`Выбран статус: ${value || 'Все статусы'}`)
              }}
            >
              <option value="">Все статусы</option>
              <option value="черновик">Черновики</option>
              <option value="опубликовано">Опубликованные</option>
              <option value="запланировано">Запланированные</option>
              <option value="архив">Архив</option>
            </select>
            <div className="selected-value">
              Текущий статус: <strong>{statusFilter || 'Все статусы'}</strong>
            </div>
          </div>
        </div>

        <div className="test-section">
          <h2>Фильтр статуса в кнопке (Liquid Glass)</h2>
          <p>Тот же фильтр, но выбранное значение отображается в стеклянной кнопке.</p>
          <div className="test-controls">
            <div className="glass-select-button-wrapper">
              <GlassButton className="glass-select-button">
                Статус: {buttonStatusFilter || 'Все статусы'}
              </GlassButton>
              <select
                className="glass-select-native"
                value={buttonStatusFilter}
                onChange={(e) => {
                  const value = e.target.value
                  setButtonStatusFilter(value)
                  addLog(`Выбран статус (кнопка): ${value || 'Все статусы'}`)
                }}
              >
                <option value="">Все статусы</option>
                <option value="черновик">Черновики</option>
                <option value="опубликовано">Опубликованные</option>
                <option value="запланировано">Запланированные</option>
                <option value="архив">Архив</option>
              </select>
            </div>
          </div>
        </div>

        <div className="test-section">
          <h2>Меню в кнопке (Liquid Glass + MobX)</h2>
          <p>Кнопка всегда показывает текст «меню», а список внутри — как у навигации. Состояние хранится в MobX store.</p>
          <div className="test-controls">
            <GlassMenuButton />
          </div>
        </div>

        <div className="test-section">
          <h2>GlassSelectKeyWithIcon - универсальный компонент</h2>
          <p>Стеклянная кнопка с select внутри и опциональной иконкой. Можно использовать для любых списков.</p>
          <div className="test-controls">
            <GlassSelectKeyWithIcon
              options={[
                { value: 'option1', label: 'Опция 1', icon: <span>🔴</span> },
                { value: 'option2', label: 'Опция 2', icon: <span>🟢</span> },
                { value: 'option3', label: 'Опция 3', icon: <span>🔵</span> },
                { value: 'option4', label: 'Опция 4', icon: <span>🟡</span> },
              ]}
              value={testSelectValue}
              onChange={(value) => {
                setTestSelectValue(value)
                addLog(`Выбрано через GlassSelectKeyWithIcon: ${value}`)
              }}
              placeholder="Выберите опцию..."
              icon={
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path
                    d="M10 2L2 7L10 12L18 7L10 2Z"
                    fill="currentColor"
                  />
                </svg>
              }
            />
            <div className="selected-value">
              Выбрано: <strong>{testSelectValue || 'Ничего'}</strong>
            </div>
          </div>
        </div>

        <div className="test-section">
          <h2>Последний выбор (меню из MobX store)</h2>
          <div className="selected-value">
            Выбрано: <strong>{uiStore.menuChoice || 'Ничего'}</strong>
          </div>
        </div>

        <div className="test-section">
          <h2>MobX + стеклянный блок фильтра</h2>
          <p>Этот блок показывает, как MobX-хранилище управляет стеклянной карточкой и кнопкой.</p>
          <GlassCard>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <strong>Фильтр района (MobX store):</strong>
              </div>
              <Dropdown
                options={simpleOptions}
                defaultText="Выберите район"
                onChange={(value) => uiStore.setDistrictFilter(String(value))}
                value={uiStore.districtFilter}
                variant="form"
                className="test-dropdown"
              />
              <div>
                Текущее значение фильтра:&nbsp;
                <strong>{uiStore.districtFilter || 'Все районы'}</strong>
              </div>

              <div style={{ marginTop: '8px' }}>
                <strong>Стеклянная кнопка (MobX + Liquid Glass):</strong>
              </div>
              <GlassButton
                onClick={() => {
                  uiStore.incrementGlassButton()
                  uiStore.setGlassMode(uiStore.glassMode === 'default' ? 'highlighted' : 'default')
                }}
                className={uiStore.glassMode === 'highlighted' ? 'glass-button--highlighted' : ''}
              >
                Нажато {uiStore.glassButtonClicks} раз
              </GlassButton>
            </div>
          </GlassCard>
        </div>

        <div className="test-section">
          <h2>Пример: Эффект стекла (glassmorphism)</h2>
          <p>Так можно оформить карточку или нижнюю панель в стиле iOS Liquid Glass.</p>
          <div className="glass-demo-wrapper">
            <GlassCard>
              <h3>Glass Card</h3>
              <p>Это пример блока с эффектом «стекла».</p>
            </GlassCard>
          </div>
          <pre className="code-block">
{`.glass-card {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}`}
          </pre>
        </div>

        <div className="test-section">
          <h2>Вариант 1: Простой выбор (как выбор района)</h2>
          <p>Имитирует выбор района - немедленная реакция при выборе</p>
          <div className="test-controls">
            <Dropdown
              options={simpleOptions}
              defaultText="Выберите район"
              onChange={handleSimpleSelect}
              value={selectedValue1}
              variant="form"
              className="test-dropdown"
            />
            <div className="selected-value">
              Выбрано: <strong>{selectedValue1 || 'Все районы'}</strong>
            </div>
          </div>
        </div>

        <div className="test-section">
          <h2>Вариант 2: Навигация (BottomNavDropdown)</h2>
          <p>Меню навигации с иконками - при выборе сразу переход на страницу</p>
          <div className="test-controls">
            <BottomNavDropdown
              options={navOptions}
              onSelect={handleNavSelect}
              triggerIcon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M3 12H21M3 6H21M3 18H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              }
              triggerLabel="Меню навигации"
            />
            <div className="selected-value">
              Выбрано: <strong>{selectedValue2 || 'Не выбрано'}</strong>
            </div>
          </div>
        </div>

        <div className="test-section">
          <h2>Вариант 3: Объекты из БД (BottomNavDropdown)</h2>
          <p>Список объектов - при выборе сразу открывается объект</p>
          <div className="test-controls">
            <BottomNavDropdown
              options={objectOptions}
              onSelect={handleObjectSelect}
              triggerIcon={
                <img 
                  src="/SVG/objects_down.svg" 
                  alt="Объекты" 
                  width="24" 
                  height="24"
                />
              }
              triggerLabel="Быстрый доступ к объектам"
              emptyText="Нет объектов"
            />
            <div className="selected-value">
              Выбран объект: <strong>{selectedValue3 || 'Не выбран'}</strong>
            </div>
          </div>
        </div>

        <div className="test-section">
          <h2>Вариант 4: С отключенными опциями</h2>
          <p>Демонстрация работы с disabled опциями</p>
          <div className="test-controls">
            <Dropdown
              options={disabledOptions}
              defaultText="Выберите опцию"
              onChange={(value) => addLog(`Выбрана опция: ${value}`)}
              variant="form"
              className="test-dropdown"
            />
          </div>
        </div>

        <div className="test-section">
          <h2>Вариант 5: Обычный Dropdown (для форм)</h2>
          <p>Стандартный Dropdown компонент для использования в формах</p>
          <div className="test-controls">
            <Dropdown
              options={simpleOptions}
              defaultText="Выберите..."
              onChange={(value) => addLog(`Dropdown выбрано: ${value}`)}
              variant="form"
              className="test-dropdown"
            />
          </div>
        </div>

        <div className="test-section">
          <h2>Лог действий</h2>
          <div className="log-box">
            {log.length === 0 ? (
              <p className="log-empty">Нет действий</p>
            ) : (
              log.map((entry, index) => (
                <div key={index} className="log-entry">
                  {entry}
                </div>
              ))
            )}
          </div>
          <button 
            className="btn btn-secondary" 
            onClick={() => setLog([])}
          >
            Очистить лог
          </button>
        </div>
      </div>
    </Layout>
  )
}

export default observer(DropdownTest)

