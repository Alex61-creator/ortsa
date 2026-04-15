import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Input, Space, Typography, message } from 'antd'
import { fetchSettings, updateSetting } from '@/api/settings'
import type { AppSettingRow } from '@/types/admin'
import dayjs from 'dayjs'

const SETTING_LABELS: Record<string, { label: string; hint: string }> = {
  synastry_repeat_price: {
    label: 'Цена повторной / дополнительной синастрии (₽)',
    hint: 'Сумма в рублях, которую платит пользователь за каждую синастрию сверх включённых в тариф. По умолчанию: 190.00',
  },
}

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettingRow[]>([])
  const [loading, setLoading] = useState(false)
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchSettings()
      setSettings(data)
      const map: Record<string, string> = {}
      data.forEach((s) => { map[s.key] = s.value })
      setValues(map)
    } catch {
      message.error('Не удалось загрузить настройки')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const handleSave = async (key: string) => {
    setSaving((prev) => ({ ...prev, [key]: true }))
    try {
      const updated = await updateSetting(key, values[key] ?? '')
      setSettings((prev) => prev.map((s) => s.key === key ? updated : s))
      message.success('Настройка сохранена')
    } catch {
      message.error('Ошибка сохранения')
    } finally {
      setSaving((prev) => ({ ...prev, [key]: false }))
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card title="Настройки приложения" loading={loading}>
        {settings.length === 0 && !loading && (
          <Typography.Text type="secondary">Настройки не загружены.</Typography.Text>
        )}

        {settings.map((s) => {
          const meta = SETTING_LABELS[s.key]
          return (
            <div key={s.key} style={{ marginBottom: 24 }}>
              <Typography.Text strong style={{ display: 'block', marginBottom: 4 }}>
                {meta?.label ?? s.key}
              </Typography.Text>
              {meta?.hint && (
                <Typography.Text
                  type="secondary"
                  style={{ display: 'block', fontSize: 12, marginBottom: 8 }}
                >
                  {meta.hint}
                </Typography.Text>
              )}
              <Space>
                <Input
                  value={values[s.key] ?? ''}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [s.key]: e.target.value }))
                  }
                  style={{ width: 200 }}
                  onPressEnter={() => void handleSave(s.key)}
                />
                <Button
                  type="primary"
                  loading={saving[s.key]}
                  onClick={() => void handleSave(s.key)}
                >
                  Сохранить
                </Button>
              </Space>
              <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 4 }}>
                Обновлено: {dayjs(s.updated_at).format('DD.MM.YYYY HH:mm')}
              </div>
            </div>
          )
        })}
      </Card>

      {/* Справка по тарифам */}
      <Card title="Включено в тарифы" size="small">
        <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left' }}>
              <th style={{ padding: '6px 12px', borderBottom: '1px solid var(--ag-border)' }}>Тариф</th>
              <th style={{ padding: '6px 12px', borderBottom: '1px solid var(--ag-border)' }}>Синастрия</th>
              <th style={{ padding: '6px 12px', borderBottom: '1px solid var(--ag-border)' }}>Лимит</th>
            </tr>
          </thead>
          <tbody>
            {[
              { code: 'free', name: 'Бесплатный', access: false, limit: '—' },
              { code: 'report', name: 'Отчёт', access: false, limit: '—' },
              { code: 'bundle', name: 'Набор 3', access: true, limit: '1 включена, далее платно' },
              { code: 'sub_monthly', name: 'Astro Pro (месяц)', access: true, limit: 'Безлимитно' },
              { code: 'sub_annual', name: 'Astro Pro (год)', access: true, limit: 'Безлимитно' },
            ].map((row) => (
              <tr key={row.code}>
                <td style={{ padding: '6px 12px', borderBottom: '1px solid var(--ag-border)' }}>
                  <code>{row.code}</code> — {row.name}
                </td>
                <td style={{ padding: '6px 12px', borderBottom: '1px solid var(--ag-border)' }}>
                  {row.access ? '✅ Да' : '❌ Нет'}
                </td>
                <td style={{ padding: '6px 12px', borderBottom: '1px solid var(--ag-border)', color: '#8c8c8c' }}>
                  {row.limit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: 12, fontSize: 12, color: '#8c8c8c' }}>
          Для выдачи доступа конкретному пользователю вне тарифа — используйте вкладку «Синастрия» в карточке пользователя.
        </div>
      </Card>
    </Space>
  )
}
