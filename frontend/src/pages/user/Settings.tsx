import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import { useAuth } from '../../contexts/AuthContext'
import { useTheme } from '../../contexts/ThemeContext'
import Dropdown, { type DropdownOption } from '../../components/Dropdown'
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
  const { theme, setTheme, availableThemes } = useTheme()
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

  // Поля объекта для отображения
  const objectDisplayFields = [
    { key: 'rooms_type', label: 'Тип комнат' },
    { key: 'price', label: 'Цена' },
    { key: 'area', label: 'Площадь' },
    { key: 'floor', label: 'Этаж' },
    { key: 'districts', label: 'Районы' },
    { key: 'address', label: 'Адрес' },
    { key: 'renovation', label: 'Ремонт' },
    { key: 'comment', label: 'Комментарий' },
  ]

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
                Выберите поля объекта для отображения в карточке объекта и списке объектов
              </p>

              <div className="form-group">
                <label className="form-label">Поля для карточки объекта (короткое описание)</label>
                <div className="checkbox-group">
                  {objectDisplayFields.map((field) => (
                    <label key={field.key} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={settings.object_card_display_types?.includes(field.key) || false}
                        onChange={(e) => {
                          const current = settings.object_card_display_types || []
                          const updated = e.target.checked
                            ? [...current, field.key]
                            : current.filter((t) => t !== field.key)
                          handleChange('object_card_display_types', updated)
                        }}
                      />
                      <span>{field.label}</span>
                    </label>
                  ))}
                </div>
                <small className="form-hint">
                  Если ничего не выбрано, будут показываться все поля
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Поля для списка объектов (одна строка)</label>
                <div className="checkbox-group">
                  {objectDisplayFields.map((field) => (
                    <label key={field.key} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={settings.object_list_display_types?.includes(field.key) || false}
                        onChange={(e) => {
                          const current = settings.object_list_display_types || []
                          const updated = e.target.checked
                            ? [...current, field.key]
                            : current.filter((t) => t !== field.key)
                          handleChange('object_list_display_types', updated)
                        }}
                      />
                      <span>{field.label}</span>
                    </label>
                  ))}
                </div>
                <small className="form-hint">
                  Если ничего не выбрано, будут показываться все поля
                </small>
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary btn-block" disabled={saving || loadingSettings}>
                {saving ? 'Сохранение...' : 'Сохранить настройки'}
              </button>
            </div>
          </form>

          <div className="form-section">
            <h3 className="card-title">Выбор темы</h3>
            <p className="card-description">
              Выберите тему оформления приложения. Изменения применяются сразу.
            </p>
            <div className="form-group">
              <label className="form-label">Тема оформления</label>
              <div className="theme-selector-wrapper">
                <Dropdown
                  options={availableThemes.map((t) => ({
                    value: t.value,
                    label: t.label,
                  })) as DropdownOption[]}
                  value={theme}
                  onChange={(value) => {
                    setTheme(value as typeof theme)
                  }}
                  placeholder="Выберите тему..."
                />
              </div>
              <small className="form-hint">
                Текущая тема: <strong>{availableThemes.find((t) => t.value === theme)?.label}</strong>
              </small>
            </div>
          </div>

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

function ClearAutopublishButton(): JSX.Element {
  const [success, setSuccess] = useState<string>('')

  const { mutate: clearAutopublish, loading, error } = useApiMutation<Record<string, never>, { success: boolean; message: string; deleted: { configs: number; publication_queues: number; account_queues: number } }>({
    url: '/user/dashboard/settings/clear-autopublish',
    method: 'POST',
    errorContext: 'Clearing autopublish',
    defaultErrorMessage: 'Ошибка при очистке автопубликации',
    onSuccess: (data) => {
      setSuccess(`Автопубликация успешно очищена. Удалено: ${data.deleted.configs} конфигураций, ${data.deleted.publication_queues + data.deleted.account_queues} задач в очереди.`)
    },
  })

  const handleClear = (): void => {
    if (!confirm('Вы уверены, что хотите снять все объекты с автопубликации и очистить очередь? Это действие нельзя отменить.')) {
      return
    }

    setSuccess('')
    void clearAutopublish({})
  }

  return (
    <div>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}
      <button
        type="button"
        className="btn btn-warning btn-block"
        onClick={handleClear}
        disabled={loading}
      >
        {loading ? 'Очистка...' : 'Снять автопубликацию и очистить очередь'}
      </button>
    </div>
  )
}

