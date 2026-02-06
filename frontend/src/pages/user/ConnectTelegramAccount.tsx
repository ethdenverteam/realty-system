import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../../components/Layout'
import { GlassCard } from '../../components/GlassCard'
import api from '../../utils/api'
import axios from 'axios'
import type { ApiErrorResponse } from '../../types/models'
import './ConnectTelegramAccount.css'

type ConnectStep = 'phone' | 'code' | '2fa'

export default function ConnectTelegramAccount(): JSX.Element {
  const navigate = useNavigate()
  const [step, setStep] = useState<ConnectStep>('phone')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [password2FA, setPassword2FA] = useState('')
  const [codeHash, setCodeHash] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const startConnection = async (): Promise<void> => {
    if (!phone.trim()) {
      setError('Введите номер телефона')
      return
    }
    
    if (!phone.startsWith('+')) {
      setError('Номер должен начинаться с + (например, +79991234567)')
      return
    }

    try {
      setLoading(true)
      setError('')
      const res = await api.post<{ success: boolean; code_hash?: string; account_id?: number; message?: string }>('/accounts/connect/start', {
        phone: phone.trim()
      })
      
      if (res.data.success) {
        if (res.data.account_id) {
          setSuccess('Аккаунт уже подключен')
          setTimeout(() => {
            navigate('/user/dashboard/telegram-accounts')
          }, 2000)
        } else if (res.data.code_hash) {
          setCodeHash(res.data.code_hash)
          setStep('code')
          setSuccess('Код подтверждения отправлен в Telegram')
        }
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка подключения')
      } else {
        setError('Ошибка подключения')
      }
    } finally {
      setLoading(false)
    }
  }

  const verifyCode = async (): Promise<void> => {
    if (!code.trim()) {
      setError('Введите код подтверждения')
      return
    }

    try {
      setLoading(true)
      setError('')
      const res = await api.post<{ success: boolean; requires_2fa?: boolean; account_id?: number; message?: string }>('/accounts/connect/verify-code', {
        phone: phone,
        code: code.trim(),
        code_hash: codeHash
      })
      
      if (res.data.success) {
        if (res.data.requires_2fa) {
          setStep('2fa')
          setSuccess('Введите пароль 2FA')
        } else {
          setSuccess('Аккаунт успешно подключен')
          setTimeout(() => {
            navigate('/user/dashboard/telegram-accounts')
          }, 2000)
        }
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка проверки кода')
      } else {
        setError('Ошибка проверки кода')
      }
    } finally {
      setLoading(false)
    }
  }

  const verify2FA = async (): Promise<void> => {
    if (!password2FA.trim()) {
      setError('Введите пароль 2FA')
      return
    }

    try {
      setLoading(true)
      setError('')
      const res = await api.post<{ success: boolean; account_id?: number; message?: string }>('/accounts/connect/verify-2fa', {
        phone: phone,
        password: password2FA.trim()
      })
      
      if (res.data.success) {
        setSuccess('Аккаунт успешно подключен')
        setTimeout(() => {
          navigate('/user/dashboard/telegram-accounts')
        }, 2000)
      }
    } catch (err: unknown) {
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        setError(err.response?.data?.error || 'Ошибка проверки 2FA')
      } else {
        setError('Ошибка проверки 2FA')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Подключение Telegram аккаунта">
      <div className="connect-telegram-page">
        {error && (
          <div className="alert alert-error" onClick={() => setError('')}>
            {error}
          </div>
        )}
        {success && (
          <div className="alert alert-success" onClick={() => setSuccess('')}>
            {success}
          </div>
        )}

        <GlassCard className="connect-card">
          <div className="connect-header">
            <h2>Подключение Telegram аккаунта</h2>
            <button className="btn btn-secondary" onClick={() => navigate('/user/dashboard/telegram-accounts')}>
              ← Назад
            </button>
          </div>

          <div className="connect-steps">
            <div className={`step-indicator ${step === 'phone' ? 'active' : step === 'code' || step === '2fa' ? 'completed' : ''}`}>
              <div className="step-number">1</div>
              <div className="step-label">Телефон</div>
            </div>
            <div className={`step-connector ${step === 'code' || step === '2fa' ? 'active' : ''}`}></div>
            <div className={`step-indicator ${step === 'code' ? 'active' : step === '2fa' ? 'completed' : ''}`}>
              <div className="step-number">2</div>
              <div className="step-label">Код</div>
            </div>
            <div className={`step-connector ${step === '2fa' ? 'active' : ''}`}></div>
            <div className={`step-indicator ${step === '2fa' ? 'active' : ''}`}>
              <div className="step-number">3</div>
              <div className="step-label">2FA</div>
            </div>
          </div>

          <div className="connect-content">
            {step === 'phone' && (
              <div className="connect-step-content">
                <label>
                  Номер телефона (формат: +79991234567)
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+79991234567"
                    disabled={loading}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !loading) {
                        void startConnection()
                      }
                    }}
                  />
                </label>
                <div className="connect-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => void startConnection()}
                    disabled={loading}
                  >
                    {loading ? 'Отправка...' : 'Отправить код'}
                  </button>
                </div>
              </div>
            )}
            
            {step === 'code' && (
              <div className="connect-step-content">
                <label>
                  Код подтверждения из Telegram
                  <input
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="12345"
                    maxLength={6}
                    disabled={loading}
                    autoFocus
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !loading) {
                        void verifyCode()
                      }
                    }}
                  />
                </label>
                <div className="connect-actions">
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      setStep('phone')
                      setCode('')
                      setError('')
                    }}
                    disabled={loading}
                  >
                    Назад
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => void verifyCode()}
                    disabled={loading}
                  >
                    {loading ? 'Проверка...' : 'Подтвердить'}
                  </button>
                </div>
              </div>
            )}
            
            {step === '2fa' && (
              <div className="connect-step-content">
                <label>
                  Пароль 2FA
                  <input
                    type="password"
                    value={password2FA}
                    onChange={(e) => setPassword2FA(e.target.value)}
                    placeholder="Пароль 2FA"
                    disabled={loading}
                    autoFocus
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !loading) {
                        void verify2FA()
                      }
                    }}
                  />
                </label>
                <div className="connect-actions">
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      setStep('code')
                      setPassword2FA('')
                      setError('')
                    }}
                    disabled={loading}
                  >
                    Назад
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => void verify2FA()}
                    disabled={loading}
                  >
                    {loading ? 'Проверка...' : 'Подтвердить'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </GlassCard>
      </div>
    </Layout>
  )
}

