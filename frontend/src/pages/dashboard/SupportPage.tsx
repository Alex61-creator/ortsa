import { useState } from 'react'
import { useTranslation } from 'react-i18next'

const SUPPORT_EMAIL = 'support@astrogen.ru'
const SUPPORT_TG = 'https://t.me/astrogen_support'
const SUPPORT_HANDLE = '@astrogen_support'

export function SupportPage() {
  const { t } = useTranslation()
  const [message, setMessage] = useState('')

  const sendMail = () => {
    const subject = encodeURIComponent(t('support.mailSubject'))
    const body = encodeURIComponent(message.trim() || '')
    window.location.href = `mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`
  }

  return (
    <div className="card" style={{ maxWidth: 600 }}>
      <div className="card-header">
        <div className="card-title">{t('support.cardTitle')}</div>
      </div>
      <div className="card-body">
        <div style={{ display: 'grid', gap: 12, marginBottom: 24 }} className="support-contact-grid">
          <a
            href={`mailto:${SUPPORT_EMAIL}`}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
              padding: 16,
              border: '1px solid var(--border)',
              borderRadius: 'var(--r)',
              textDecoration: 'none',
              transition: 'all 0.15s',
            }}
            className="support-contact-card"
          >
            <span style={{ fontSize: 20 }}>✉</span>
            <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)' }}>{t('support.email')}</span>
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{SUPPORT_EMAIL}</span>
          </a>
          <a
            href={SUPPORT_TG}
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
              padding: 16,
              border: '1px solid var(--border)',
              borderRadius: 'var(--r)',
              textDecoration: 'none',
              transition: 'all 0.15s',
            }}
            className="support-contact-card"
          >
            <span style={{ fontSize: 20 }}>✈</span>
            <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)' }}>{t('support.telegram')}</span>
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{SUPPORT_HANDLE}</span>
          </a>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="support-message">
            {t('support.formLabel')}
          </label>
          <textarea
            id="support-message"
            className="form-input"
            rows={4}
            style={{ resize: 'vertical' }}
            placeholder={t('support.placeholder')}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
        </div>
        <button type="button" className="btn btn-primary" onClick={sendMail}>
          {t('support.send')}
        </button>
        <div style={{ marginTop: 14, fontSize: 12, color: 'var(--text-3)' }}>{t('support.responseTime')}</div>
      </div>
    </div>
  )
}
