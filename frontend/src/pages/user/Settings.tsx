import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { useAuth } from '../../contexts/AuthContext'
import { ContactSettings } from '../../components/settings/ContactSettings'
import { DisplaySettings } from '../../components/settings/DisplaySettings'
import { ThemeSettings } from '../../components/settings/ThemeSettings'
import { ClearAutopublishButton } from '../../components/settings/ClearAutopublishButton'
import { useApiData } from '../../hooks/useApiData'
import { useApiMutation } from '../../hooks/useApiMutation'
import { PHONE_PATTERN, PHONE_ERROR_MESSAGE } from '../../utils/constants'
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
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')

  // Загрузка настроек
  const { data: settingsData, loading: loadingSettings } = useApiData<UserSettings>({
    url: '/user/dashboard/settings/data',
    errorContext: 'Loading settings',
    defaultErrorMessage: 'Ошибка загрузки настроек',
  })
  
  const [settings, setSettings] = useState<UserSettings>({
    phone: '',
    contact_name: '',
    default_show_username: false,
    object_card_display_types: [],
    object_list_display_types: [],
  })

  const handleLogout = (): void => {
    if (confirm('Вам придется заново зайти через код. Вы уверены, что хотите выйти?')) {
      void logout()
    }
  }

  // Применение загруженных настроек
  useEffect(() => {
    if (settingsData) {
      setSettings(settingsData)
    }
  }, [settingsData])

  // Сохранение настроек
  const { mutate: saveSettings, loading: saving } = useApiMutation<UserSettings, unknown>({
    url: '/user/dashboard/settings/data',
    method: 'PUT',
    errorContext: 'Saving settings',
    defaultErrorMessage: 'Ошибка сохранения настроек',
    onSuccess: () => {
      setSuccess('Настройки успешно сохранены!')
    },
  })

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')
    setSuccess('')
    
    // Валидация телефона
    if (settings.phone && settings.phone.trim()) {
      if (!PHONE_PATTERN.test(settings.phone.trim())) {
        setError(PHONE_ERROR_MESSAGE)
        return
      }
    }
    
    await saveSettings(settings)
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
        <GlassCard>
          <h2 className="card-title">Настройка контактов</h2>
          <p className="card-description">
            Эти настройки будут использоваться по умолчанию при создании новых объектов
          </p>

          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}

          <form onSubmit={handleSubmit} className="settings-form">
            <ContactSettings settings={settings} onChange={handleChange} />
            <DisplaySettings settings={settings} onChange={handleChange} />
            <div className="form-actions">
              <button type="submit" className="btn btn-primary btn-block" disabled={saving || loadingSettings}>
                {saving ? 'Сохранение...' : 'Сохранить настройки'}
              </button>
            </div>
          </form>

          <ThemeSettings />

          <div className="form-section">
            <h3 className="card-title">Управление автопубликацией</h3>
            <p className="card-description">
              Снять все объекты с автопубликации и очистить очередь публикаций. После этого можно будет вручную передобавить объекты на автопубликацию.
            </p>
            <ClearAutopublishButton />
          </div>

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
        </GlassCard>
      </div>
    </Layout>
  )
}


