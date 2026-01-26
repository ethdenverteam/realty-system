import axios from 'axios'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import './CreateObject.css'

interface CreateObjectFormData {
  rooms_type: string
  price: string
  area: string
  floor: string
  districts: string
  comment: string
  address: string
  renovation: string
  contact_name: string
  phone_number: string
  show_username: boolean
}

interface CreateObjectResponse {
  success?: boolean
  object_id?: number | string
}

export default function UserCreateObject(): JSX.Element {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState<CreateObjectFormData>({
    rooms_type: '',
    price: '',
    area: '',
    floor: '',
    districts: '',
    comment: '',
    address: '',
    renovation: '',
    contact_name: '',
    phone_number: '',
    show_username: false,
  })

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const districts = formData.districts
        .split(',')
        .map((d) => d.trim())
        .filter((d) => d)

      const response = await api.post<CreateObjectResponse>('/objects/', {
        rooms_type: formData.rooms_type,
        price: parseFloat(formData.price),
        area: formData.area ? parseFloat(formData.area) : null,
        floor: formData.floor,
        districts_json: districts,
        comment: formData.comment,
        address: formData.address,
        renovation: formData.renovation,
        contact_name: formData.contact_name,
        phone_number: formData.phone_number,
        show_username: formData.show_username,
      })

      if (response.data.success || response.data.object_id) {
        navigate('/user/dashboard/objects', { replace: true })
      } else {
        setError('Ошибка при создании объекта')
      }
    } catch (err: unknown) {
      const message = axios.isAxiosError(err)
        ? (err.response?.data as any)?.error || 'Ошибка при создании объекта'
        : 'Ошибка при создании объекта'
      setError(String(message))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Создать объект">
      <div className="create-object-page">
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="create-object-form">
          <div className="form-section">
            <h3 className="section-title">Основная информация</h3>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Тип комнат *</label>
                <select
                  className="form-input"
                  value={formData.rooms_type}
                  onChange={(e) => setFormData({ ...formData, rooms_type: e.target.value })}
                  required
                >
                  <option value="">Выберите тип</option>
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
              </div>
              <div className="form-group">
                <label className="form-label">Цена (тыс. руб.) *</label>
                <input
                  type="number"
                  className="form-input"
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                  step="0.01"
                  min="0"
                  required
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Площадь (м²) *</label>
                <input
                  type="number"
                  className="form-input"
                  value={formData.area}
                  onChange={(e) => setFormData({ ...formData, area: e.target.value })}
                  step="0.01"
                  min="0"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Этаж</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.floor}
                  onChange={(e) => setFormData({ ...formData, floor: e.target.value })}
                  placeholder="например: 5/9"
                />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Районы</label>
              <input
                type="text"
                className="form-input"
                value={formData.districts}
                onChange={(e) => setFormData({ ...formData, districts: e.target.value })}
                placeholder="Введите районы через запятую"
              />
              <small className="form-hint">Например: ККБ, Музыкальный</small>
            </div>
          </div>

          <div className="form-section">
            <h3 className="section-title">Описание</h3>
            <div className="form-group">
              <label className="form-label">Комментарий</label>
              <textarea
                className="form-input"
                rows={4}
                value={formData.comment}
                onChange={(e) => setFormData({ ...formData, comment: e.target.value })}
                placeholder="Опишите квартиру и условия покупки"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Адрес</label>
              <input
                type="text"
                className="form-input"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Улица и номер дома"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Состояние ремонта</label>
              <select
                className="form-input"
                value={formData.renovation}
                onChange={(e) => setFormData({ ...formData, renovation: e.target.value })}
              >
                <option value="">Не указано</option>
                <option value="Черновая">Черновая</option>
                <option value="ПЧО">ПЧО</option>
                <option value="Ремонт требует освежения">Ремонт требует освежения</option>
                <option value="Хороший ремонт">Хороший ремонт</option>
                <option value="Инстаграмный">Инстаграмный</option>
              </select>
            </div>
          </div>

          <div className="form-section">
            <h3 className="section-title">Контакты</h3>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Имя контакта</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.contact_name}
                  onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Телефон</label>
                <input
                  type="tel"
                  className="form-input"
                  value={formData.phone_number}
                  onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  placeholder="+79991234567"
                />
              </div>
            </div>
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.show_username}
                  onChange={(e) => setFormData({ ...formData, show_username: e.target.checked })}
                />
                <span>Показывать username Telegram</span>
              </label>
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? 'Создание...' : 'Создать объект'}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-block"
              onClick={() => navigate('/user/dashboard/objects')}
            >
              Отмена
            </button>
          </div>
        </form>
      </div>
    </Layout>
  )
}


