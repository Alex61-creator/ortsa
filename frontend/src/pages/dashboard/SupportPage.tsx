import { useState } from 'react'
import { useTranslation } from 'react-i18next'

const SUPPORT_EMAIL = 'support@astrogen.ru'
const SUPPORT_TG = 'https://t.me/astrogen_support'
const SUPPORT_HANDLE = '@astrogen_support'

export function SupportPage() {
  const { t } = useTranslation()
  const [message, setMessage] = useState('')
  const [topic, setTopic] = useState('Вопрос об оплате или заказе')
  const [openFaq, setOpenFaq] = useState<number | null>(0)

  const faqItems = [
    {
      q: 'Когда будет готов PDF-отчёт?',
      a: 'PDF-отчёт формируется автоматически сразу после оплаты — обычно в течение 1–3 минут. Ссылка придёт на email и появится в разделе «Отчёты и PDF».',
    },
    {
      q: 'Как отменить подписку?',
      a: 'Перейдите в раздел «Подписка» и нажмите «Отменить подписку». Доступ к Pro сохраняется до конца оплаченного периода.',
    },
    {
      q: 'Можно ли изменить натальные данные?',
      a: 'Да, в разделе «Натальные данные». Но учтите: изменение данных не пересчитывает уже купленные отчёты — для нового расчёта нужно создать новый заказ.',
    },
    {
      q: 'Как долго хранятся мои отчёты?',
      a: 'Все купленные PDF-отчёты хранятся бессрочно в вашем кабинете в разделе «Отчёты и PDF».',
    },
    {
      q: 'Что входит в Набор «3»?',
      a: 'Набор включает 3 полных PDF-отчёта для разных людей. Это разовая покупка без подписки — доступ бессрочный.',
    },
    {
      q: 'Я не получил чек или письмо с PDF',
      a: 'Проверьте папку «Спам». Если письмо так и не пришло — напишите нам через форму или в Telegram и укажите номер заказа.',
    },
  ]

  const sendMail = () => {
    const subject = encodeURIComponent(`${t('support.mailSubject')}: ${topic}`)
    const body = encodeURIComponent(message.trim() || '')
    window.location.href = `mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`
  }

  return (
    <div className="support-grid">
      <div className="card">
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
            <label className="form-label" htmlFor="support-topic">
              Тема
            </label>
            <select
              id="support-topic"
              className="form-input"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            >
              <option>Вопрос об оплате или заказе</option>
              <option>Технический вопрос</option>
              <option>Вопрос о подписке</option>
              <option>Другое</option>
            </select>
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
      <div className="support-right">
        <div className="card">
          <div className="card-header">
            <div className="card-title">Часто задаваемые вопросы</div>
          </div>
          <div className="card-body">
            {faqItems.map((item, idx) => (
              <div className="faq-item" key={item.q}>
                <button
                  type="button"
                  className="faq-q"
                  onClick={() => setOpenFaq((prev) => (prev === idx ? null : idx))}
                >
                  {item.q} <span>{openFaq === idx ? '▴' : '▾'}</span>
                </button>
                {openFaq === idx && <div className="faq-a">{item.a}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
