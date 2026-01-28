import { useState, useEffect } from 'react'
import axios from 'axios'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import { useAuth } from '../../contexts/AuthContext'
import type { ApiErrorResponse } from '../../types/models'
import './Settings.css'

interface UserSettings {
  phone: string
  contact_name: string
  default_show_username: boolean
  object_card_display_types?: string[]
  object_list_display_types?: string[]
}

export default function UserSettings(): JSX.Element {
  const { logout } = useAuth()
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const [settings, setSettings] = useState<UserSettings>({
    phone: '',
    contact_name: '',
    default_show_username: false,
    object_card_display_types: [],
    object_list_display_types: [],
  })

  const roomsTypes = ['Студия', '1к', '2к', '3к', '4+к', 'Дом', '1евро', 'евро1к', '2евро', 'евро2к', '3евро', 'евро3к']

  const handleLogout = (): void => {
    if (confirm('Вам придется заново зайти через код. Вы уверены, что хотите выйти?')) {
      void logout()
    }
  }

  useEffect(() => {
    void loadSettings()
  }, [])

  const loadSettings = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const response = await api.get<UserSettings>('/user/dashboard/settings/data')
      setSettings(response.data)
    } catch (err: unknown) {
      let message = 'Ошибка загрузки настроек'
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        message = err.response?.data?.error || err.message || message
      }
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')
    setSuccess('')
    
    // Validate phone number format if provided
    if (settings.phone && settings.phone.trim()) {
      const phonePattern = /^8\d{10}$/
      if (!phonePattern.test(settings.phone.trim())) {
        setError('Номер телефона должен быть в формате 89693386969 (11 цифр, начинается с 8)')
        return
      }
    }
    
    setLoading(true)

    try {
      await api.put('/user/dashboard/settings/data', settings)
      setSuccess('Настройки успешно сохранены!')
    } catch (err: unknown) {
      let message = 'Ошибка сохранения настроек'
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        message = err.response?.data?.error || err.response?.data?.details || err.message || message
      }
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof UserSettings, value: string | boolean | string[]): void => {
    setSettings({
      ...settings,
      [field]: value,
    })
  }

  return (
    <Layout title="Настройки контактов">
      <div className="settings-page">
        <div className="card">
          <h2 className="card-title">Настройка контактов</h2>
          <p className="card-description">
            Эти настройки будут использоваться по умолчанию при создании новых объектов
          </p>

          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}

          <form onSubmit={handleSubmit} className="settings-form">
            <div className="form-section">
              <div className="form-group">
                <label className="form-label">Номер телефона</label>
                <input
                  type="tel"
                  className="form-input"
                  value={settings.phone}
                  onChange={(e) => handleChange('phone', e.target.value)}
                  placeholder="89693386969"
                  pattern="^8\d{10}$"
                  title="Номер должен быть в формате 89693386969 (11 цифр, начинается с 8)"
                />
                <small className="form-hint">Формат: 89693386969 (11 цифр, начинается с 8)</small>
              </div>

              <div className="form-group">
                <label className="form-label">Имя контакта</label>
                <input
                  type="text"
                  className="form-input"
                  value={settings.contact_name}
                  onChange={(e) => handleChange('contact_name', e.target.value)}
                  placeholder="Ваше имя"
                />
                <small className="form-hint">Имя будет отображаться в объявлениях</small>
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={settings.default_show_username}
                    onChange={(e) => handleChange('default_show_username', e.target.checked)}
                  />
                  <span>Показывать username Telegram по умолчанию</span>
                </label>
                <small className="form-hint">
                  При создании новых объектов будет включено отображение вашего Telegram username
                </small>
              </div>
            </div>

            <div className="form-section">
              <h3 className="card-title">Настройки отображения объектов</h3>
              <p className="card-description">
                Выберите типы объектов для отображения в карточке объекта и списке объектов
              </p>

              <div className="form-group">
                <label className="form-label">Типы для карточки объекта (короткое описание)</label>
                <div className="checkbox-group">
                  {roomsTypes.map((type) => (
                    <label key={type} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={settings.object_card_display_types?.includes(type) || false}
                        onChange={(e) => {
                          const current = settings.object_card_display_types || []
                          const updated = e.target.checked
                            ? [...current, type]
                            : current.filter((t) => t !== type)
                          handleChange('object_card_display_types', updated)
                        }}
                      />
                      <span>{type}</span>
                    </label>
                  ))}
                </div>
                <small className="form-hint">
                  Если ничего не выбрано, будут показываться все типы
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Типы для списка объектов (одна строка)</label>
                <div className="checkbox-group">
                  {roomsTypes.map((type) => (
                    <label key={type} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={settings.object_list_display_types?.includes(type) || false}
                        onChange={(e) => {
                          const current = settings.object_list_display_types || []
                          const updated = e.target.checked
                            ? [...current, type]
                            : current.filter((t) => t !== type)
                          handleChange('object_list_display_types', updated)
                        }}
                      />
                      <span>{type}</span>
                    </label>
                  ))}
                </div>
                <small className="form-hint">
                  Если ничего не выбрано, будут показываться все типы
                </small>
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                {loading ? 'Сохранение...' : 'Сохранить настройки'}
              </button>
            </div>
          </form>

          <div className="settings-logout-section">
            <h3 className="card-title">Выход</h3>
            <p className="card-description">
              Выйти из системы. Вам придется заново зайти через код.
            </p>
            <button
              type="button"
              className="btn btn-danger btn-block"
              onClick={handleLogout}
            >
              Выйти
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}

