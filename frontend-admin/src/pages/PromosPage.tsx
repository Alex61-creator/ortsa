import { useEffect, useState } from 'react'
import { Button, Card, DatePicker, Form, Input, InputNumber, Switch, message } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '@/api/client'
import { createPromo, fetchPromos, patchPromo } from '@/api/promos'
import type { PromoRow } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const { RangePicker } = DatePicker

async function downloadRedemptionsCsv(params: {
  date_from?: string
  date_to?: string
  promo_code?: string
}) {
  const { data } = await api.get<Blob>('/api/v1/admin/export/promocode-redemptions.csv', {
    params: { ...params, excel_bom: 1 },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'promocode_redemptions.csv'
  a.click()
  window.URL.revokeObjectURL(url)
}

function statusTag(active: boolean) {
  return active
    ? <span className="ag-tag ag-tag-green">active</span>
    : <span className="ag-tag ag-tag-gray">inactive</span>
}

function usageBadge(used: number, max: number) {
  const pct = max > 0 ? Math.round((used / max) * 100) : 0
  const color = pct >= 90 ? 'var(--ag-danger)' : pct >= 60 ? 'var(--ag-warning)' : 'var(--ag-success)'
  return (
    <span style={{ fontSize: 12, color }}>
      {used} / {max}
    </span>
  )
}

export function PromosPage() {
  const [rows, setRows]     = useState<PromoRow[]>([])
  const [form]              = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [exportRange, setExportRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null)
  const [exportCode, setExportCode] = useState('')
  const [exportLoading, setExportLoading] = useState(false)

  const load = () => {
    setLoading(true)
    void fetchPromos()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const active   = rows.filter((r) => r.is_active).length
  const inactive = rows.filter((r) => !r.is_active).length
  const totalUsed = rows.reduce((acc, r) => acc + r.used_count, 0)

  return (
    <>
      {/* ── KPI row ── */}
      <div className="admin-metric-grid" style={{ marginBottom: 18 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Всего промокодов</div>
          <div className="admin-metric-value">{rows.length}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">в системе</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Активных</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-success)' }}>{active}</div>
          <div className="admin-metric-delta admin-metric-delta--up">доступно к применению</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Неактивных</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-muted)' }}>{inactive}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">отключено</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Использований</div>
          <div className="admin-metric-value">{totalUsed}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">всего применений</div>
        </div>
      </div>

      {/* ── Create form ── */}
      <Card title="Новый промокод" style={{ marginBottom: 16 }}>
        <Form
          form={form}
          layout="inline"
          onFinish={(v) =>
            void createPromo({
              ...v,
              active_until: v.active_until?.toISOString?.() ?? null,
            })
              .then(() => {
                message.success('Промокод создан')
                form.resetFields()
                load()
              })
              .catch(() => message.error('Не удалось создать промокод'))
          }
        >
          <Form.Item name="code" rules={[{ required: true, message: '' }]}>
            <Input
              placeholder="КОД"
              style={{ textTransform: 'uppercase', width: 140, fontFamily: 'monospace' }}
            />
          </Form.Item>
          <Form.Item name="discount_percent" rules={[{ required: true, message: '' }]}>
            <InputNumber min={1} max={100} placeholder="% скидки" addonAfter="%" style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="max_uses" initialValue={100} rules={[{ required: true, message: '' }]}>
            <InputNumber min={1} placeholder="Лимит" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="active_until">
            <DatePicker showTime placeholder="Срок действия" style={{ width: 180 }} />
          </Form.Item>
          <Button htmlType="submit" type="primary">
            Создать
          </Button>
        </Form>
      </Card>

      {/* ── Promo list ── */}
      <Card title="Список промокодов" bodyStyle={{ padding: '0' }}>
        {/* Header */}
        <div
          className="ag-promo-row"
          style={{
            background: 'var(--ag-card-soft)',
            borderRadius: '10px 10px 0 0',
            padding: '8px 18px',
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--ag-muted)',
            textTransform: 'uppercase',
            letterSpacing: '.05em',
            borderBottom: '1px solid var(--ag-border)',
          }}
        >
          <span>Код</span>
          <span>Скидка</span>
          <span>Использовано</span>
          <span>До</span>
          <span>Статус</span>
          <span>Вкл</span>
        </div>

        {loading ? (
          <div className="admin-empty" style={{ margin: 20 }}>Загрузка…</div>
        ) : rows.length === 0 ? (
          <div className="admin-empty" style={{ margin: 20 }}>Промокоды не созданы</div>
        ) : (
          <div style={{ padding: '0 18px' }}>
            {rows.map((row) => (
              <div key={row.id} className="ag-promo-row">
                <span
                  style={{
                    fontFamily: 'monospace',
                    fontSize: 13,
                    fontWeight: 600,
                    color: 'var(--ag-text)',
                  }}
                >
                  {row.code}
                </span>
                <span style={{ fontWeight: 500 }}>{row.discount_percent}%</span>
                <span>{usageBadge(row.used_count, row.max_uses)}</span>
                <span style={{ fontSize: 12, color: 'var(--ag-muted)' }}>
                  {row.active_until
                    ? new Date(row.active_until).toLocaleDateString('ru-RU')
                    : '∞'}
                </span>
                <span>{statusTag(row.is_active)}</span>
                <Switch
                  size="small"
                  checked={row.is_active}
                  onChange={(v) =>
                    void patchPromo(row.id, { is_active: v })
                      .then(() => {
                        message.success('Статус обновлён')
                        load()
                      })
                      .catch((e) =>
                        message.error(extractApiErrorMessage(e, 'Не удалось обновить'))
                      )
                  }
                />
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Выгрузка использований промокодов" style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <div style={{ fontSize: 12, marginBottom: 4, color: 'var(--ag-muted)' }}>Период</div>
            <RangePicker
              value={exportRange}
              onChange={(v) => setExportRange(v as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null)}
            />
          </div>
          <div>
            <div style={{ fontSize: 12, marginBottom: 4, color: 'var(--ag-muted)' }}>Промокод (фильтр)</div>
            <Input
              placeholder="Все"
              value={exportCode}
              onChange={(e) => setExportCode(e.target.value.toUpperCase())}
              style={{ width: 160 }}
              allowClear
            />
          </div>
          <Button
            icon={<DownloadOutlined />}
            loading={exportLoading}
            onClick={() => {
              setExportLoading(true)
              const params: Record<string, string> = {}
              if (exportRange?.[0]) params.date_from = exportRange[0].toISOString()
              if (exportRange?.[1]) params.date_to = exportRange[1].toISOString()
              if (exportCode.trim()) params.promo_code = exportCode.trim()
              void downloadRedemptionsCsv(params)
                .catch(() => message.error('Не удалось скачать CSV'))
                .finally(() => setExportLoading(false))
            }}
          >
            Скачать CSV
          </Button>
        </div>
      </Card>
    </>
  )
}
