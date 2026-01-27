import { useState } from 'react'
import Layout from '../../../components/Layout'
import { ObjectCard } from '../../../components/ObjectCard'
import { ObjectsList } from '../../../components/ObjectsList'
import { GlassCard } from '../../../components/GlassCard'
import { GlassButton } from '../../../components/GlassButton'
import type { RealtyObjectListItem } from '../../../types/models'
import './Test.css'

/**
 * Тестовая страница для отладки компонентов карточки объекта и списка объектов
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

  const handleObjectClick = (obj: RealtyObjectListItem): void => {
    setSelectedObject(obj)
    console.log('Clicked object:', obj)
  }

  return (
    <Layout title="Тест: Карточка объекта и список объектов" isAdmin>
      <div className="test-page">
        <div className="test-section">
          <h2>1. Карточка объекта</h2>
          <p>Одиночная карточка объекта с эффектом жидкого стекла</p>
          <div className="test-card-wrapper">
            <ObjectCard object={testObject} onClick={() => handleObjectClick(testObject)} />
          </div>
        </div>

        <div className="test-section">
          <h2>2. Список объектов</h2>
          <p>Список объектов с карточками</p>
          <div className="test-list-wrapper">
            <ObjectsList objects={testObjects} onObjectClick={handleObjectClick} />
          </div>
        </div>

        {selectedObject && (
          <div className="test-section">
            <h2>Выбранный объект</h2>
            <GlassCard>
              <pre>{JSON.stringify(selectedObject, null, 2)}</pre>
            </GlassCard>
          </div>
        )}

        <div className="test-section">
          <h2>Тест стеклянных кнопок с glow эффектом</h2>
          <div className="test-buttons-wrapper">
            <GlassButton onClick={() => console.log('Button 1 clicked')}>
              Кнопка 1
            </GlassButton>
            <GlassButton onClick={() => console.log('Button 2 clicked')}>
              Кнопка 2
            </GlassButton>
            <GlassButton onClick={() => console.log('Button 3 clicked')}>
              Кнопка 3
            </GlassButton>
          </div>
        </div>
      </div>
    </Layout>
  )
}

