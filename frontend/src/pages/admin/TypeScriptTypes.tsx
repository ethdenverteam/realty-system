import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import './TypeScriptTypes.css'

/**
 * Страница со списком всех типизаций TypeScript в проекте
 * Показывает все интерфейсы, типы и их параметры
 */
export default function TypeScriptTypes(): JSX.Element {
  const types = [
    {
      name: 'User',
      category: 'User Management',
      description: 'Интерфейс пользователя системы',
      properties: [
        { name: 'web_role', type: "WebRole ('admin' | 'user')", required: true, description: 'Роль пользователя в системе' },
        { name: '[key: string]', type: 'unknown', required: false, description: 'Дополнительные свойства' },
      ],
    },
    {
      name: 'AdminStats',
      category: 'Statistics',
      description: 'Статистика для админ панели',
      properties: [
        { name: 'users_count', type: 'number', required: true, description: 'Количество пользователей' },
        { name: 'objects_count', type: 'number', required: true, description: 'Количество объектов' },
        { name: 'publications_today', type: 'number', required: true, description: 'Публикаций сегодня' },
        { name: 'accounts_count', type: 'number', required: true, description: 'Активных аккаунтов' },
      ],
    },
    {
      name: 'UserStats',
      category: 'Statistics',
      description: 'Статистика для пользователя',
      properties: [
        { name: 'objects_count', type: 'number', required: true, description: 'Количество объектов' },
        { name: 'total_publications', type: 'number', required: true, description: 'Всего публикаций' },
        { name: 'today_publications', type: 'number', required: true, description: 'Публикаций сегодня' },
        { name: 'accounts_count', type: 'number', required: true, description: 'Количество аккаунтов' },
        { name: 'autopublish_objects_count', type: 'number', required: false, description: 'Объектов на автопубликации' },
      ],
    },
    {
      name: 'RealtyObject',
      category: 'Objects',
      description: 'Полная информация об объекте недвижимости',
      properties: [
        { name: 'object_id', type: 'string', required: true, description: 'ID объекта' },
        { name: 'status', type: 'string', required: true, description: 'Статус объекта' },
        { name: 'rooms_type', type: 'string | null', required: false, description: 'Тип комнат' },
        { name: 'price', type: 'number', required: true, description: 'Цена в тысячах рублей' },
        { name: 'area', type: 'number | null', required: false, description: 'Площадь в м²' },
        { name: 'floor', type: 'string | null', required: false, description: 'Этаж' },
        { name: 'districts_json', type: 'string[] | null', required: false, description: 'Районы' },
        { name: 'comment', type: 'string | null', required: false, description: 'Комментарий' },
        { name: 'address', type: 'string | null', required: false, description: 'Адрес' },
        { name: 'renovation', type: 'string | null', required: false, description: 'Состояние ремонта' },
        { name: 'contact_name', type: 'string | null', required: false, description: 'Имя контакта' },
        { name: 'phone_number', type: 'string | null', required: false, description: 'Номер телефона' },
        { name: 'show_username', type: 'boolean', required: false, description: 'Показывать username Telegram' },
        { name: 'photos_json', type: 'string[] | null', required: false, description: 'Массив путей к фотографиям' },
        { name: 'creation_date', type: 'string | null', required: false, description: 'Дата создания' },
        { name: 'publication_date', type: 'string | null', required: false, description: 'Дата публикации' },
        { name: 'user_id', type: 'number | string | null', required: false, description: 'ID пользователя' },
        { name: 'can_publish', type: 'boolean', required: false, description: 'Можно ли опубликовать' },
        { name: 'last_publication', type: 'string | null', required: false, description: 'Последняя публикация' },
      ],
    },
    {
      name: 'RealtyObjectListItem',
      category: 'Objects',
      description: 'Краткая информация об объекте для списка',
      properties: [
        { name: 'object_id', type: 'number | string', required: true, description: 'ID объекта' },
        { name: 'status', type: 'string', required: true, description: 'Статус объекта' },
        { name: 'rooms_type', type: 'string | null', required: false, description: 'Тип комнат' },
        { name: 'price', type: 'number', required: true, description: 'Цена в тысячах рублей' },
        { name: 'area', type: 'number | null', required: false, description: 'Площадь в м²' },
        { name: 'floor', type: 'string | null', required: false, description: 'Этаж' },
        { name: 'districts_json', type: 'string[] | null', required: false, description: 'Районы' },
        { name: 'comment', type: 'string | null', required: false, description: 'Комментарий' },
        { name: 'can_publish', type: 'boolean', required: false, description: 'Можно ли опубликовать' },
        { name: 'last_publication', type: 'string | null', required: false, description: 'Последняя публикация' },
      ],
    },
    {
      name: 'ObjectFormData',
      category: 'Forms',
      description: 'Данные формы создания/редактирования объекта',
      properties: [
        { name: 'rooms_type', type: 'string', required: true, description: 'Тип комнат' },
        { name: 'price', type: 'string', required: true, description: 'Цена (строка для формы)' },
        { name: 'area', type: 'string', required: true, description: 'Площадь (строка для формы)' },
        { name: 'floor', type: 'string', required: true, description: 'Этаж' },
        { name: 'districts', type: 'string', required: true, description: 'Районы (через запятую)' },
        { name: 'comment', type: 'string', required: true, description: 'Комментарий' },
        { name: 'address', type: 'string', required: true, description: 'Адрес' },
        { name: 'renovation', type: 'string', required: true, description: 'Состояние ремонта' },
        { name: 'contact_name', type: 'string', required: true, description: 'Имя контакта' },
        { name: 'phone_number', type: 'string', required: true, description: 'Номер телефона' },
        { name: 'show_username', type: 'boolean', required: true, description: 'Показывать username Telegram' },
      ],
    },
    {
      name: 'RoomsType',
      category: 'Enums',
      description: 'Типы комнат',
      properties: [
        { name: 'Студия', type: 'literal', required: true, description: 'Студия' },
        { name: '1к', type: 'literal', required: true, description: '1 комната' },
        { name: '2к', type: 'literal', required: true, description: '2 комнаты' },
        { name: '3к', type: 'literal', required: true, description: '3 комнаты' },
        { name: '4+к', type: 'literal', required: true, description: '4+ комнат' },
        { name: 'Дом', type: 'literal', required: true, description: 'Дом' },
        { name: 'евро1к', type: 'literal', required: true, description: 'Евро 1к' },
        { name: 'евро2к', type: 'literal', required: true, description: 'Евро 2к' },
        { name: 'евро3к', type: 'literal', required: true, description: 'Евро 3к' },
      ],
    },
    {
      name: 'RenovationType',
      category: 'Enums',
      description: 'Типы ремонта',
      properties: [
        { name: 'Черновая', type: 'literal', required: true, description: 'Черновая отделка' },
        { name: 'ПЧО', type: 'literal', required: true, description: 'Предчистовая отделка' },
        { name: 'Ремонт требует освежения', type: 'literal', required: true, description: 'Требует освежения' },
        { name: 'Хороший ремонт', type: 'literal', required: true, description: 'Хороший ремонт' },
        { name: 'Инстаграмный', type: 'literal', required: true, description: 'Инстаграмный ремонт' },
      ],
    },
  ]

  const categories = Array.from(new Set(types.map((t) => t.category)))

  return (
    <Layout title="TypeScript Типизации" isAdmin>
      <div className="typescript-types-page">
        <GlassCard>
          <h2>Список всех типизаций TypeScript</h2>
          <p>Полный список интерфейсов, типов и их параметров в проекте</p>
        </GlassCard>

        {categories.map((category) => (
          <GlassCard key={category} className="types-category">
            <h3 className="category-title">{category}</h3>
            {types
              .filter((t) => t.category === category)
              .map((type) => (
                <div key={type.name} className="type-item">
                  <div className="type-header">
                    <h4 className="type-name">{type.name}</h4>
                    <span className="type-badge">{type.category}</span>
                  </div>
                  <p className="type-description">{type.description}</p>
                  <div className="type-properties">
                    <h5>Параметры:</h5>
                    <table className="properties-table">
                      <thead>
                        <tr>
                          <th>Имя</th>
                          <th>Тип</th>
                          <th>Обязательный</th>
                          <th>Описание</th>
                        </tr>
                      </thead>
                      <tbody>
                        {type.properties.map((prop, idx) => (
                          <tr key={idx}>
                            <td className="prop-name">
                              <code>{prop.name}</code>
                            </td>
                            <td className="prop-type">
                              <code>{prop.type}</code>
                            </td>
                            <td className="prop-required">{prop.required ? '✓' : '✗'}</td>
                            <td className="prop-description">{prop.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
          </GlassCard>
        ))}
      </div>
    </Layout>
  )
}

