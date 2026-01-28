import { useState } from 'react'
import Layout from '../../../components/Layout'
import { ObjectCard } from '../../../components/ObjectCard'
import { ObjectsList } from '../../../components/ObjectsList'
import { GlassCard } from '../../../components/GlassCard'
import { GlassButton } from '../../../components/GlassButton'
import Dropdown, { type DropdownOption } from '../../../components/Dropdown'
import GlassSelectKeyWithIcon, { type GlassSelectOption } from '../../../components/GlassSelectKeyWithIcon'
import MobileSelect from '../../../components/MobileSelect'
import BottomNavDropdown from '../../../components/BottomNavDropdown'
import MobileDropdownMenu from '../../../components/MobileDropdownMenu'
import QuickAccessObjects from '../../../components/QuickAccessObjects'
import type { RealtyObjectListItem } from '../../../types/models'
import './Test.css'

/**
 * Тестовая страница со всеми компонентами системы
 */
export default function Test(): JSX.Element {
  // Тестовые данные
  const testObject: RealtyObjectListItem = {
    object_id: 1,
    rooms_type: 'Студия',
    price: 1000,
    status: 'черновик',
    area: 35,
    floor: '5/10',
    districts_json: ['Центральный', 'Северный'],
    comment: 'Уютная студия в центре города с хорошим ремонтом и видом на парк.',
  }

  const testObjects: RealtyObjectListItem[] = [
    { object_id: 1, rooms_type: 'Студия', price: 1000, status: 'черновик', area: 35, floor: '5/10', districts_json: ['Центральный'] },
    { object_id: 2, rooms_type: '1к', price: 1500, status: 'опубликовано', area: 45, floor: '3/9', districts_json: ['Северный'] },
    { object_id: 3, rooms_type: '2к', price: 2000, status: 'черновик', area: 60, floor: '7/12', districts_json: ['Южный'] },
  ]

  const [selectedObject, setSelectedObject] = useState<RealtyObjectListItem | null>(null)
  const [dropdownValue, setDropdownValue] = useState<string | number>('')
  const [glassSelectValue, setGlassSelectValue] = useState<string | number>('option1')
  const [mobileSelectValue, setMobileSelectValue] = useState<string>('')

  const dropdownOptions: DropdownOption[] = [
    { label: 'Опция 1', value: 'option1' },
    { label: 'Опция 2', value: 'option2' },
    { label: 'Опция 3', value: 'option3' },
  ]

  const glassSelectOptions: GlassSelectOption[] = [
    { label: 'Опция 1', value: 'option1' },
    { label: 'Опция 2', value: 'option2' },
    { label: 'Опция 3', value: 'option3' },
  ]

  const mobileSelectOptions = [
    { label: 'Опция 1', value: 'option1' },
    { label: 'Опция 2', value: 'option2' },
    { label: 'Опция 3', value: 'option3' },
  ]

  const bottomNavOptions: DropdownOption[] = [
    { label: 'Главная', value: '/admin/dashboard', icon: <span>🏠</span> },
    { label: 'Чаты', value: '/admin/dashboard/bot-chats', icon: <span>💬</span> },
    { label: 'Логи', value: '/admin/dashboard/logs', icon: <span>📋</span> },
  ]

  const handleObjectClick = (obj: RealtyObjectListItem): void => {
    setSelectedObject(obj)
    console.log('Clicked object:', obj)
  }

  const handleBottomNavSelect = (value: string | number): void => {
    console.log('Selected:', value)
  }

  return (
    <Layout title="Тесты компонентов" isAdmin>
      <div className="test-page">
        <GlassCard>
          <h1>Каталог компонентов</h1>
          <p>Демонстрация всех компонентов системы с их свойствами и вариантами использования</p>
        </GlassCard>

        {/* GlassButton */}
        <div className="test-section">
          <h2>1. GlassButton</h2>
          <p><strong>Описание:</strong> Стеклянная кнопка с эффектом glow при клике</p>
          <p><strong>Props:</strong> icon?: ReactNode, children?: ReactNode, className?: string, onClick?: () =&gt; void</p>
          <div className="test-buttons-wrapper">
            <GlassButton onClick={() => console.log('Button 1 clicked')}>
              Кнопка без иконки
            </GlassButton>
            <GlassButton 
              icon={<span>⭐</span>}
              onClick={() => console.log('Button 2 clicked')}
            >
              Кнопка с иконкой
            </GlassButton>
            <GlassButton onClick={() => console.log('Button 3 clicked')}>
              Еще одна кнопка
            </GlassButton>
          </div>
        </div>

        {/* GlassCard */}
        <div className="test-section">
          <h2>2. GlassCard</h2>
          <p><strong>Описание:</strong> Стеклянная карточка с эффектом glassmorphism</p>
          <p><strong>Props:</strong> children: ReactNode, className?: string, onClick?: () =&gt; void</p>
          <div className="test-cards-wrapper">
            <GlassCard>
              <h3>Простая карточка</h3>
              <p>Это содержимое карточки без обработчика клика</p>
            </GlassCard>
            <GlassCard onClick={() => console.log('Card clicked')}>
              <h3>Кликабельная карточка</h3>
              <p>Эта карточка имеет обработчик onClick и будет светиться при клике</p>
            </GlassCard>
          </div>
        </div>

        {/* Dropdown */}
        <div className="test-section">
          <h2>3. Dropdown</h2>
          <p><strong>Описание:</strong> Выпадающее меню с опциями</p>
          <p><strong>Props:</strong> options: DropdownOption[], value?: string | number, onChange: (value) =&gt; void, placeholder?: string, label?: string, variant?: 'default' | 'mobile' | 'form'</p>
          <div className="test-dropdown-wrapper">
            <Dropdown
              options={dropdownOptions}
              value={dropdownValue}
              onChange={setDropdownValue}
              placeholder="Выберите опцию..."
              label="Пример Dropdown"
            />
            <p>Выбрано: {dropdownValue || 'ничего'}</p>
          </div>
        </div>

        {/* GlassSelectKeyWithIcon */}
        <div className="test-section">
          <h2>4. GlassSelectKeyWithIcon</h2>
          <p><strong>Описание:</strong> Стеклянная кнопка с select внутри, показывает только иконку</p>
          <p><strong>Props:</strong> options: GlassSelectOption[], value: string | number, onChange: (value) =&gt; void, placeholder?: string, icon?: ReactNode, className?: string</p>
          <div className="test-glass-select-wrapper">
            <GlassSelectKeyWithIcon
              options={glassSelectOptions}
              value={glassSelectValue}
              onChange={setGlassSelectValue}
              placeholder="Выберите..."
              icon={
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 3V1M12 23V21M21 12H23M1 12H3M18.364 5.636L19.778 4.222M4.222 19.778L5.636 18.364M18.364 18.364L19.778 19.778M4.222 4.222L5.636 5.636M17 12C17 14.7614 14.7614 17 12 17C9.23858 17 7 14.7614 7 12C7 9.23858 9.23858 7 12 7C14.7614 7 17 9.23858 17 12Z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              }
            />
            <p>Выбрано: {glassSelectValue}</p>
          </div>
        </div>

        {/* MobileSelect */}
        <div className="test-section">
          <h2>5. MobileSelect</h2>
          <p><strong>Описание:</strong> Мобильный селект с выпадающим меню</p>
          <p><strong>Props:</strong> value: string, onChange: (value) =&gt; void, options: MobileSelectOption[], placeholder?: string, label?: string, className?: string</p>
          <div className="test-mobile-select-wrapper">
            <MobileSelect
              value={mobileSelectValue}
              onChange={setMobileSelectValue}
              options={mobileSelectOptions}
              placeholder="Выберите опцию..."
              label="Пример MobileSelect"
            />
            <p>Выбрано: {mobileSelectValue || 'ничего'}</p>
          </div>
        </div>

        {/* BottomNavDropdown */}
        <div className="test-section">
          <h2>6. BottomNavDropdown</h2>
          <p><strong>Описание:</strong> Выпадающее меню для нижней панели навигации</p>
          <p><strong>Props:</strong> options: DropdownOption[], onSelect: (value) =&gt; void, triggerIcon: ReactNode, triggerLabel: string, emptyText?: string, className?: string</p>
          <div className="test-bottom-nav-wrapper">
            <BottomNavDropdown
              options={bottomNavOptions}
              onSelect={handleBottomNavSelect}
              triggerIcon={<span>📱</span>}
              triggerLabel="Навигация"
            />
          </div>
        </div>

        {/* MobileDropdownMenu */}
        <div className="test-section">
          <h2>7. MobileDropdownMenu</h2>
          <p><strong>Описание:</strong> Мобильное выпадающее меню</p>
          <p><strong>Props:</strong> objects?: RealtyObjectListItem[], onObjectSelect?: (id) =&gt; void, type?: 'menu' | 'objects'</p>
          <div className="test-mobile-dropdown-wrapper">
            <MobileDropdownMenu
              objects={testObjects}
              onObjectSelect={(id) => console.log('Object selected:', id)}
              type="objects"
            />
          </div>
        </div>

        {/* QuickAccessObjects */}
        <div className="test-section">
          <h2>8. QuickAccessObjects</h2>
          <p><strong>Описание:</strong> Быстрый доступ к объектам</p>
          <p><strong>Props:</strong> objects: RealtyObjectListItem[], onClose?: () =&gt; void</p>
          <div className="test-quick-access-wrapper">
            <QuickAccessObjects
              objects={testObjects}
              onClose={() => console.log('Quick access closed')}
            />
          </div>
        </div>

        {/* ObjectCard */}
        <div className="test-section">
          <h2>9. ObjectCard</h2>
          <p><strong>Описание:</strong> Карточка объекта недвижимости</p>
          <p><strong>Props:</strong> object: RealtyObjectListItem, onClick?: () =&gt; void</p>
          <div className="test-card-wrapper">
            <ObjectCard object={testObject} onClick={() => handleObjectClick(testObject)} />
          </div>
        </div>

        {/* ObjectsList */}
        <div className="test-section">
          <h2>10. ObjectsList</h2>
          <p><strong>Описание:</strong> Список объектов недвижимости</p>
          <p><strong>Props:</strong> objects: RealtyObjectListItem[], onObjectClick?: (object) =&gt; void</p>
          <div className="test-list-wrapper">
            <ObjectsList objects={testObjects} onObjectClick={handleObjectClick} />
          </div>
        </div>

        {/* Selected Object Info */}
        {selectedObject && (
          <div className="test-section">
            <h2>Выбранный объект</h2>
            <GlassCard>
              <pre>{JSON.stringify(selectedObject, null, 2)}</pre>
            </GlassCard>
          </div>
        )}
      </div>
    </Layout>
  )
}
