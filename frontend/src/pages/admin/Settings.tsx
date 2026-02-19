import { useEffect, useState } from 'react'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import './Settings.css'

interface AdminSettings {
  allow_duplicates: boolean
  admin_bypass_time_limit: boolean
}

export default function AdminSettings(): JSX.Element {
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    void loadSettings()
  }, [])

  const loadSettings = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<{ success: boolean; settings: AdminSettings }>('/admin/dashboard/settings')
      if (res.data.success) {
        setSettings(res.data.settings)
      }
    } catch (err: unknown) {
      console.error('Error loading settings:', err)
      const message = err instanceof Error ? err.message : 'Ошибка загрузки настроек'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleDuplicates = async (enabled: boolean): Promise<void> => {
    try {
      setSaving(true)
      setError('')
      setSuccess('')

      await api.put('/admin/dashboard/settings/allow-duplicates', { enabled })

      setSettings((prev) => (prev ? { ...prev, allow_duplicates: enabled } : null))
      setSuccess('Настройка успешно обновлена')
    } catch (err: unknown) {
      console.error('Error updating setting:', err)
      const message = err instanceof Error ? err.message : 'Ошибка обновления настройки'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  const handleToggleTimeLimit = async (enabled: boolean): Promise<void> => {
    try {
      setSaving(true)
      setError('')
      setSuccess('')

      await api.put('/admin/dashboard/settings/admin-bypass-time-limit', { enabled })

      setSettings((prev) => (prev ? { ...prev, admin_bypass_time_limit: enabled } : null))
      setSuccess('Настройка успешно обновлена')
    } catch (err: unknown) {
      console.error('Error updating setting:', err)
      const message = err instanceof Error ? err.message : 'Ошибка обновления настройки'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Layout title="Настройки системы" isAdmin>
      <div className="admin-settings">
        <GlassCard>
          <h2 className="card-title">Настройки системы</h2>
          <p style={{ fontSize: '14px', color: 'rgba(255, 255, 255, 0.7)', marginBottom: '20px' }}>
            Управление системными настройками автопубликации
          </p>

          {loading && <div className="loading">Загрузка настроек...</div>}

          {error && (
            <div className="alert alert-error" style={{ marginBottom: '20px' }}>
              {error}
            </div>
          )}

          {success && (
            <div className="alert alert-success" style={{ marginBottom: '20px' }}>
              {success}
            </div>
          )}

          {!loading && settings && (
            <div className="settings-list">
              <div className="setting-item">
                <div className="setting-info">
                  <h3>Разрешить дубликаты публикаций</h3>
                  <p className="setting-description">
                    Если включено, разрешает публикацию одного и того же объекта в один и тот же чат
                    в течение 24 часов. Если выключено, система проверяет дубликаты и не публикует повторно.
                  </p>
                </div>
                <div className="setting-control">
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={settings.allow_duplicates}
                      onChange={(e) => {
                        void handleToggleDuplicates(e.target.checked)
                      }}
                      disabled={saving}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                  <span className="setting-status">
                    {settings.allow_duplicates ? 'Включено' : 'Выключено'}
                  </span>
                </div>
              </div>

              <div className="setting-item">
                <div className="setting-info">
                  <h3>Админ: отключить ограничение времени (8:00-22:00)</h3>
                  <p className="setting-description">
                    Если включено, админ может публиковать объекты через бота и аккаунты в любое время суток,
                    без ограничения рабочими часами (8:00-22:00 МСК). Для обычных пользователей ограничение остается.
                  </p>
                </div>
                <div className="setting-control">
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={settings.admin_bypass_time_limit}
                      onChange={(e) => {
                        void handleToggleTimeLimit(e.target.checked)
                      }}
                      disabled={saving}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                  <span className="setting-status">
                    {settings.admin_bypass_time_limit ? 'Включено' : 'Выключено'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </GlassCard>
      </div>
    </Layout>
  )
}

