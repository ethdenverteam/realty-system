import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { uiStore } from '../../stores/uiStore'
import { observer } from 'mobx-react-lite'
import './MobXStore.css'

/**
 * Страница с описанием всех элементов MobX store
 * Показывает состояние, методы и их параметры
 */
function MobXStore(): JSX.Element {
  const storeElements = [
    {
      name: 'districtFilter',
      type: 'string',
      category: 'State',
      description: 'Фильтр района для демонстрации работы стеклянных компонентов',
      defaultValue: "''",
      currentValue: uiStore.districtFilter || "''",
      methods: [
        {
          name: 'setDistrictFilter',
          parameters: [{ name: 'value', type: 'string', description: 'Новое значение фильтра' }],
          description: 'Устанавливает значение фильтра района',
        },
      ],
    },
    {
      name: 'glassMode',
      type: "'default' | 'highlighted'",
      category: 'State',
      description: 'Режим отображения стеклянной карточки',
      defaultValue: "'default'",
      currentValue: `'${uiStore.glassMode}'`,
      methods: [
        {
          name: 'setGlassMode',
          parameters: [
            { name: 'mode', type: "'default' | 'highlighted'", description: 'Новый режим отображения' },
          ],
          description: 'Устанавливает режим отображения стеклянной карточки',
        },
      ],
    },
    {
      name: 'glassButtonClicks',
      type: 'number',
      category: 'State',
      description: 'Счетчик нажатий на стеклянную кнопку',
      defaultValue: '0',
      currentValue: String(uiStore.glassButtonClicks),
      methods: [
        {
          name: 'incrementGlassButton',
          parameters: [],
          description: 'Увеличивает счетчик нажатий на стеклянную кнопку на 1',
        },
      ],
    },
    {
      name: 'menuChoice',
      type: 'string',
      category: 'State',
      description: 'Выбранный пункт меню навигации',
      defaultValue: "''",
      currentValue: uiStore.menuChoice || "''",
      methods: [
        {
          name: 'setMenuChoice',
          parameters: [{ name: 'value', type: 'string', description: 'Выбранное значение меню' }],
          description: 'Устанавливает выбранный пункт меню навигации',
        },
      ],
    },
    {
      name: 'selectedObjectId',
      type: 'string',
      category: 'State',
      description: 'Выбранный ID объекта для стеклянной кнопки объектов',
      defaultValue: "''",
      currentValue: uiStore.selectedObjectId || "''",
      methods: [
        {
          name: 'setSelectedObjectId',
          parameters: [{ name: 'value', type: 'string', description: 'ID выбранного объекта' }],
          description: 'Устанавливает выбранный ID объекта',
        },
      ],
    },
  ]

  return (
    <Layout title="MobX Store Элементы" isAdmin>
      <div className="mobx-store-page">
        <GlassCard>
          <h2>Элементы MobX Store</h2>
          <p>Полное описание состояния и методов UIStore с параметрами</p>
        </GlassCard>

        {storeElements.map((element) => (
          <GlassCard key={element.name} className="store-element">
            <div className="element-header">
              <div>
                <h3 className="element-name">{element.name}</h3>
                <span className="element-badge">{element.category}</span>
              </div>
              <div className="element-type">
                <code>{element.type}</code>
              </div>
            </div>

            <p className="element-description">{element.description}</p>

            <div className="element-values">
              <div className="value-item">
                <strong>Значение по умолчанию:</strong>
                <code>{element.defaultValue}</code>
              </div>
              <div className="value-item">
                <strong>Текущее значение:</strong>
                <code className="current-value">{element.currentValue}</code>
              </div>
            </div>

            {element.methods && element.methods.length > 0 && (
              <div className="element-methods">
                <h4>Методы:</h4>
                {element.methods.map((method, idx) => (
                  <div key={idx} className="method-item">
                    <div className="method-signature">
                      <code className="method-name">{method.name}</code>
                      <span className="method-params">
                        (
                        {method.parameters.length > 0
                          ? method.parameters
                              .map((p) => `${p.name}: ${p.type}`)
                              .join(', ')
                          : ''}
                        )
                      </span>
                    </div>
                    <p className="method-description">{method.description}</p>
                    {method.parameters.length > 0 && (
                      <div className="method-parameters">
                        <strong>Параметры:</strong>
                        <ul>
                          {method.parameters.map((param, pIdx) => (
                            <li key={pIdx}>
                              <code>{param.name}</code> ({param.type}): {param.description}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </GlassCard>
        ))}
      </div>
    </Layout>
  )
}

export default observer(MobXStore)

