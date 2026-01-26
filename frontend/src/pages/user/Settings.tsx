import { useState, useEffect } from 'react'
import axios from 'axios'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import type { ApiErrorResponse } from '../../types/models'
import './Settings.css'

interface UserSettings {
  phone: string
  contact_name: string
  default_show_username: boolean
}

export default function UserSettings(): JSX.Element {
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const [settings, setSettings] = useState<UserSettings>({
    phone: '',
    contact_name: '',
    default_show_username: false,
  })

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
    setLoading(true)

    try {
      await api.put('/user/dashboard/settings/data', settings)
      setSuccess('Настройки успешно сохранены!')
    } catch (err: unknown) {
      let message = 'Ошибка сохранения настроек'
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        message = err.response?.data?.error || err.message || message
      }
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof UserSettings, value: string | boolean): void => {
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
                  placeholder="+79991234567"
                />
                <small className="form-hint">Номер будет использоваться для контактов в объявлениях</small>
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

            <div className="form-actions">
              <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                {loading ? 'Сохранение...' : 'Сохранить настройки'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  )
}

