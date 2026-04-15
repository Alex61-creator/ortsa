import { useEffect, useState } from 'react'
import { Button, Card, message, Modal, Select, Tabs, Typography } from 'antd'
import { listPrompts, savePrompt, resetPrompt, type PromptTemplate } from '@/api/prompts'

const { Text, Paragraph } = Typography

const TARIFF_LABELS: Record<string, string> = {
  free: 'Free (Бесплатный)',
  report: 'Report (Полный отчёт)',
  bundle: 'Bundle (Набор 3)',
  sub_monthly: 'Sub Monthly (Подписка / месяц)',
  sub_annual: 'Sub Annual (Подписка / год)',
}

const LOCALE_LABELS: Record<string, string> = {
  ru: 'RU — Русский',
  en: 'EN — English',
}

const TARIFF_CODES = ['free', 'report', 'bundle', 'sub_monthly', 'sub_annual']

export function PromptsPage() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selectedCode, setSelectedCode] = useState<string>('free')
  const [locale, setLocale] = useState<string>('ru')
  const [editText, setEditText] = useState<string>('')
  const [isDirty, setIsDirty] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const data = await listPrompts()
      setTemplates(data)
    } catch {
      message.error('Не удалось загрузить промпты')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const current = templates.find((t) => t.tariff_code === selectedCode && t.locale === locale)

  useEffect(() => {
    if (current) {
      setEditText(current.system_prompt)
      setIsDirty(false)
    }
  }, [current?.tariff_code, current?.locale, current?.system_prompt])

  const handleSave = async () => {
    if (!editText.trim()) { message.warning('Промпт не может быть пустым'); return }
    setSaving(true)
    try {
      await savePrompt(selectedCode, locale, editText)
      message.success('Промпт сохранён')
      setIsDirty(false)
      await load()
    } catch {
      message.error('Не удалось сохранить промпт')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    Modal.confirm({
      title: 'Сбросить промпт к умолчанию?',
      content: `Тариф: ${TARIFF_LABELS[selectedCode] ?? selectedCode}, язык: ${locale.toUpperCase()}`,
      okText: 'Сбросить',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await resetPrompt(selectedCode, locale)
          message.success('Промпт сброшен к умолчанию')
          setIsDirty(false)
          await load()
        } catch {
          message.error('Ошибка сброса')
        }
      },
    })
  }

  return (
    <div>
      {/* ── KPI strip ── */}
      <div className="ag-kpi-grid" style={{ marginBottom: 16 }}>
        {TARIFF_CODES.map((code) => {
          const customRu = templates.find((t) => t.tariff_code === code && t.locale === 'ru' && t.is_custom)
          const customEn = templates.find((t) => t.tariff_code === code && t.locale === 'en' && t.is_custom)
          return (
            <div key={code} className="ag-kpi-card" style={{ cursor: 'pointer' }} onClick={() => setSelectedCode(code)}>
              <div className="ag-kpi-label">{TARIFF_LABELS[code] ?? code}</div>
              <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                <span className={`ag-tag ${customRu ? 'ag-tag-teal' : 'ag-tag-gray'}`}>RU {customRu ? 'custom' : 'default'}</span>
                <span className={`ag-tag ${customEn ? 'ag-tag-teal' : 'ag-tag-gray'}`}>EN {customEn ? 'custom' : 'default'}</span>
              </div>
            </div>
          )
        })}
      </div>

      <Card>
        {/* ── Toolbar ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <Select
            value={selectedCode}
            onChange={(v) => setSelectedCode(v)}
            style={{ width: 260 }}
            options={TARIFF_CODES.map((c) => ({ label: TARIFF_LABELS[c] ?? c, value: c }))}
          />
          <Tabs
            size="small"
            activeKey={locale}
            onChange={(k) => setLocale(k)}
            items={[
              { key: 'ru', label: 'RU' },
              { key: 'en', label: 'EN' },
            ]}
            style={{ marginBottom: 0 }}
          />
          {current?.is_custom && (
            <span className="ag-tag ag-tag-teal" style={{ marginLeft: 'auto' }}>
              Кастомный
            </span>
          )}
          {!current?.is_custom && (
            <span className="ag-tag ag-tag-gray" style={{ marginLeft: 'auto' }}>
              По умолчанию
            </span>
          )}
        </div>

        {/* ── Metadata ── */}
        {current?.is_custom && current.updated_at && (
          <div style={{ marginBottom: 10, fontSize: 12, color: 'var(--ag-muted)' }}>
            Обновлён: {new Date(current.updated_at).toLocaleString('ru-RU')}
            {current.updated_by ? ` · ${current.updated_by}` : ''}
          </div>
        )}

        {/* ── Editor ── */}
        <div style={{ position: 'relative' }}>
          <textarea
            value={editText}
            onChange={(e) => { setEditText(e.target.value); setIsDirty(true) }}
            rows={22}
            style={{
              width: '100%',
              fontFamily: 'monospace',
              fontSize: 13,
              lineHeight: 1.55,
              padding: '12px',
              border: `1px solid ${isDirty ? 'var(--ag-primary)' : 'var(--ag-border)'}`,
              borderRadius: 'var(--ag-r)',
              background: 'var(--ag-bg-container)',
              color: 'var(--ag-text-1)',
              resize: 'vertical',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
          <div style={{ position: 'absolute', bottom: 10, right: 10, fontSize: 11, color: 'var(--ag-muted)' }}>
            {editText.length} символов
          </div>
        </div>

        <Paragraph style={{ fontSize: 12, color: 'var(--ag-muted)', marginTop: 8 }}>
          Статическая часть промпта. Динамическая часть (данные клиента и Kerykeion) добавляется автоматически во время генерации.
          Маркеры разделов <Text code>## [РАЗДЕЛ]</Text> определяют структуру PDF-отчёта.
        </Paragraph>

        {/* ── Actions ── */}
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <Button
            type="primary"
            loading={saving}
            disabled={!isDirty}
            onClick={() => void handleSave()}
          >
            Сохранить
          </Button>
          {current?.is_custom && (
            <Button danger onClick={handleReset}>
              Сбросить к умолчанию
            </Button>
          )}
          <Button onClick={() => { setEditText(current?.system_prompt ?? ''); setIsDirty(false) }}>
            Отменить
          </Button>
        </div>
      </Card>
    </div>
  )
}
