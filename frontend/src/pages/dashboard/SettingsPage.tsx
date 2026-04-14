import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import i18n from 'i18next'
import { Button, Checkbox, Modal } from 'antd'
import { deleteAccount, exportUserData, fetchMe, patchMeConsent } from '@/api/users'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'

const LS_DELIVERY_EMAIL = 'astrogen_delivery_email_override'
const LS_PDF_NOTIFY = 'astrogen_pdf_notify_pdf'

function providerLabel(provider: string | null, t: (k: string) => string): string {
  if (!provider) return t('settings.providerUnknown')
  const p = provider.toLowerCase()
  if (p.includes('google')) return 'Google'
  if (p.includes('yandex')) return 'Yandex'
  if (p.includes('apple')) return 'Apple'
  if (p.includes('telegram')) return 'Telegram'
  return provider
}

export function SettingsPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const logout = useAuthStore((s) => s.logout)
  const themeMode = useThemeStore((s) => s.mode)
  const setThemeMode = useThemeStore((s) => s.setMode)

  const { data: me, isLoading } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

  const [deliveryDraft, setDeliveryDraft] = useState('')
  const [deliveryOpen, setDeliveryOpen] = useState(false)
  const [pdfNotify, setPdfNotify] = useState(() => {
    try {
      return localStorage.getItem(LS_PDF_NOTIFY) !== '0'
    } catch {
      return true
    }
  })

  const patchConsent = useMutation({
    mutationFn: (v: boolean) => patchMeConsent(v),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['me'] }),
  })

  const deliveryDisplay = () => {
    try {
      return localStorage.getItem(LS_DELIVERY_EMAIL) || me?.email || ''
    } catch {
      return me?.email || ''
    }
  }

  const saveDelivery = () => {
    try {
      if (deliveryDraft.trim()) localStorage.setItem(LS_DELIVERY_EMAIL, deliveryDraft.trim())
    } catch {
      /* ignore */
    }
    setDeliveryOpen(false)
  }

  const openDeliveryEditor = () => {
    setDeliveryDraft(deliveryDisplay())
    setDeliveryOpen((v) => !v)
  }

  const onExport = async () => {
    const blob = await exportUserData()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'user_data_export.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const onDelete = () => {
    Modal.confirm({
      title: t('settings.deleteTitle'),
      content: (
        <div>
          <p>{t('settings.deleteBody', { email: me?.email })}</p>
          <p style={{ color: 'var(--danger)', fontSize: 13, marginTop: 12 }}>{t('settings.deleteWarn')}</p>
        </div>
      ),
      okText: t('profile.deleteAccount'),
      okType: 'danger',
      cancelText: t('common.cancel'),
      onOk: async () => {
        await deleteAccount()
        logout()
        window.location.href = '/'
      },
    })
  }

  const origin = typeof window !== 'undefined' ? window.location.origin : ''

  if (isLoading || !me) return null

  const hasConsent = Boolean(me.consent_given_at)
  const lang = i18n.language?.startsWith('en') ? 'en' : 'ru'

  return (
    <div>
      <div className="settings-grid">
        <div className="settings-section">
          <div className="settings-section-title">{t('settings.sectionAccount')}</div>
          <div className="settings-row">
            <div>
              <div className="settings-label">{t('settings.loginMethod')}</div>
              <div className="settings-value">{t('settings.loginMethodHint')}</div>
            </div>
            <div className="provider-badge">
              {providerLabel(me.oauth_provider, t) === 'Google' && (
                <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden>
                  <path
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    fill="#4285F4"
                  />
                  <path
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    fill="#34A853"
                  />
                  <path
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                    fill="#FBBC05"
                  />
                  <path
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    fill="#EA4335"
                  />
                </svg>
              )}
              {providerLabel(me.oauth_provider, t)}
            </div>
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-label">{t('settings.accountEmail')}</div>
              <div className="settings-value">{me.email}</div>
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-4)' }}>{t('settings.emailFromProvider')}</span>
          </div>
          {!hasConsent && (
            <div className="settings-row">
              <div className="settings-label">{t('profile.consent')}</div>
              <Button loading={patchConsent.isPending} onClick={() => void patchConsent.mutate(true)}>
                {t('settings.acceptConsent')}
              </Button>
            </div>
          )}
        </div>

        <div className="settings-section">
          <div className="settings-section-title">{t('settings.sectionUi')}</div>
          <div className="settings-row">
            <div className="settings-label">{t('settings.language')}</div>
            <div className="segment">
              <button
                type="button"
                className={`segment-btn${lang === 'ru' ? ' on' : ''}`}
                onClick={() => void i18n.changeLanguage('ru')}
              >
                RU
              </button>
              <button
                type="button"
                className={`segment-btn${lang === 'en' ? ' on' : ''}`}
                onClick={() => void i18n.changeLanguage('en')}
              >
                EN
              </button>
            </div>
          </div>
          <div className="settings-row">
            <div className="settings-label">{t('settings.themeUi')}</div>
            <div className="segment">
              <button
                type="button"
                className={`segment-btn${themeMode === 'light' ? ' on' : ''}`}
                onClick={() => setThemeMode('light')}
              >
                ☀ {t('settings.themeLight')}
              </button>
              <button
                type="button"
                className={`segment-btn${themeMode === 'dark' ? ' on' : ''}`}
                onClick={() => setThemeMode('dark')}
              >
                ☾ {t('settings.themeDark')}
              </button>
            </div>
          </div>
          <div className="settings-row">
            <div className="settings-label">{t('settings.emailNotif')}</div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <Checkbox
                checked={pdfNotify}
                onChange={(e) => {
                  const v = e.target.checked
                  setPdfNotify(v)
                  try {
                    localStorage.setItem(LS_PDF_NOTIFY, v ? '1' : '0')
                  } catch {
                    /* ignore */
                  }
                }}
              />
              <span style={{ fontSize: 13, color: 'var(--text-2)' }}>{t('settings.pdfNotifyHint')}</span>
            </label>
          </div>
        </div>

        <div className="settings-section">
          <div className="settings-section-title">{t('settings.sectionDelivery')}</div>
          <div className="settings-row">
            <div style={{ flex: 1 }}>
              <div className="settings-label">{t('settings.deliveryPdfEmail')}</div>
              <div className="settings-value">{t('settings.deliveryHint')}</div>
            </div>
          </div>
          <div className="delivery-email-block">
            <div className="delivery-change-row">
              <div
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r)',
                  padding: '9px 14px',
                  flex: 1,
                  fontSize: 14,
                  color: 'var(--text)',
                }}
              >
                {deliveryDisplay()}
              </div>
              <button type="button" className="btn btn-default btn-sm" onClick={openDeliveryEditor}>
                {t('settings.change')}
              </button>
            </div>
            {deliveryOpen && (
              <div className="delivery-field show" style={{ display: 'block', marginTop: 12 }}>
                <div className="form-group">
                  <label className="form-label">{t('settings.newDeliveryEmail')}</label>
                  <input
                    type="email"
                    className="form-input"
                    value={deliveryDraft}
                    onChange={(e) => setDeliveryDraft(e.target.value)}
                    placeholder="other@email.com"
                  />
                  <div className="form-hint">{t('settings.deliveryFormHint')}</div>
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button type="button" className="btn btn-primary btn-sm" onClick={saveDelivery}>
                    {t('common.save')}
                  </button>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDeliveryOpen(false)}>
                    {t('common.cancel')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="settings-section">
          <div className="settings-section-title">{t('settings.sectionLegal')}</div>
          <div className="settings-row">
            <div className="settings-label">{t('settings.documents')}</div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <a href={`${origin}/oferta`} style={{ fontSize: 13 }}>
                {t('settings.linkOferta')}
              </a>
              <a href={`${origin}/privacy`} style={{ fontSize: 13 }}>
                {t('settings.linkPrivacy')}
              </a>
            </div>
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-label">{t('settings.exportLabel')}</div>
              <div className="settings-value">{t('settings.exportHint')}</div>
            </div>
            <button type="button" className="btn btn-default btn-sm" onClick={() => void onExport()}>
              {t('settings.exportCta')}
            </button>
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-label" style={{ color: 'var(--danger)' }}>
                {t('settings.deleteLabel')}
              </div>
              <div className="settings-value">{t('settings.deleteHint')}</div>
            </div>
            <button type="button" className="btn btn-danger btn-sm" onClick={onDelete}>
              {t('profile.deleteAccount')}
            </button>
          </div>
        </div>

        <div className="settings-section settings-section--wide">
          <div className="settings-section-title">{t('settings.sectionSession')}</div>
          <div className="settings-row">
            <div>
              <div className="settings-label">{t('settings.logoutLabel')}</div>
              <div className="settings-value">{t('settings.logoutHint')}</div>
            </div>
            <button
              type="button"
              className="btn btn-default btn-sm"
              onClick={() => {
                logout()
                window.location.href = '/'
              }}
            >
              {t('dashboard.logout')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
