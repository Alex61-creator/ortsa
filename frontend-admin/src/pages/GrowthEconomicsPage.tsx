import { useEffect, useMemo, useState } from 'react'
import { Button, Card, DatePicker, Form, Input, InputNumber, Select, Table, message } from 'antd'
import dayjs from 'dayjs'
import { createMarketingSpend, fetchMarketingSpend, fetchMetricsCohorts, fetchMetricsEconomics, fetchMetricsFunnel, fetchMetricsOverview } from '@/api/metrics'
import type { CohortRow, MarketingSpendRow, MetricsEconomicsOut, MetricsOverviewOut } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const { RangePicker } = DatePicker

function fmtMoney(value: number) {
  return `${value.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ₽`
}

function fmtPercent(value: number) {
  return `${(value * 100).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%`
}

export function GrowthEconomicsPage() {
  const [period, setPeriod] = useState('current_month')
  const [overview, setOverview] = useState<MetricsOverviewOut | null>(null)
  const [economics, setEconomics] = useState<MetricsEconomicsOut | null>(null)
  const [cohorts, setCohorts] = useState<CohortRow[]>([])
  const [spendRows, setSpendRows] = useState<MarketingSpendRow[]>([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const [overviewData, economicsData, cohortData, spendData] = await Promise.all([
        fetchMetricsOverview({ period }),
        fetchMetricsEconomics({ period }),
        fetchMetricsCohorts({ period }),
        fetchMarketingSpend(),
        fetchMetricsFunnel({ period }),
      ])
      setOverview(overviewData)
      setEconomics(economicsData)
      setCohorts(cohortData.rows)
      setSpendRows(spendData)
    } catch (error) {
      message.error(extractApiErrorMessage(error, 'Не удалось загрузить growth-метрики'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [period])

  const spendTotal = useMemo(
    () => spendRows.reduce((acc, row) => acc + parseFloat(row.spend_amount || '0'), 0),
    [spendRows],
  )

  return (
    <>
      <Card style={{ marginBottom: 16 }}>
        <div className="admin-toolbar">
          <Select
            value={period}
            onChange={setPeriod}
            style={{ width: 220 }}
            options={[
              { value: 'current_month', label: 'Текущий месяц' },
              { value: 'wow', label: 'Последние 7 дней' },
              { value: 'qoq', label: 'Последние 90 дней' },
            ]}
          />
          <Button onClick={() => void load()} loading={loading}>Обновить</Button>
          <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--ag-muted)' }}>
            Last touch attribution · RUB only
          </span>
        </div>
      </Card>

      <div className="admin-kpi-grid" style={{ marginBottom: 16 }}>
        {overview?.cards.map((card) => (
          <div key={card.key} className="admin-metric-card">
            <div className="admin-metric-label">{card.label}</div>
            <div className="admin-metric-value">
              {card.unit === 'RUB' ? fmtMoney(card.value) : card.unit === 'ratio' ? fmtPercent(card.value) : card.value}
            </div>
            <div className="admin-metric-delta admin-metric-delta--dim">
              {card.delta_pct == null ? 'без сравнения' : `${card.delta_pct >= 0 ? '+' : ''}${card.delta_pct.toFixed(1)}%`}
            </div>
            {card.hint && <div style={{ marginTop: 8, fontSize: 12, color: 'var(--ag-muted)' }}>{card.hint}</div>}
          </div>
        ))}
      </div>

      {!!overview?.alerts.length && (
        <Card title="Alerts" style={{ marginBottom: 16 }}>
          {overview.alerts.map((alert) => (
            <div key={alert} className="admin-info-notice" style={{ marginBottom: 8 }}>
              {alert}
            </div>
          ))}
        </Card>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 16, marginBottom: 16 }}>
        <Card title="Unit Economics">
          <div className="ag-roi-row"><span>Blended CAC</span><strong>{economics ? fmtMoney(economics.blended_cac) : '—'}</strong></div>
          <div className="ag-roi-row"><span>LTV / CAC</span><strong>{economics?.ltv_cac?.toFixed(2) ?? '—'}</strong></div>
          <div className="ag-roi-row"><span>AOV</span><strong>{economics ? fmtMoney(economics.aov) : '—'}</strong></div>
          <div className="ag-roi-row"><span>Attach-rate</span><strong>{economics ? fmtPercent(economics.attach_rate) : '—'}</strong></div>
          <div className="ag-roi-row"><span>Contribution Margin</span><strong>{economics ? fmtPercent(economics.contribution_margin) : '—'}</strong></div>
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--ag-muted)' }}>
            Action hints:
          </div>
          {economics?.action_hints.map((hint) => (
            <div key={hint} style={{ marginTop: 6, fontSize: 13 }}>{hint}</div>
          ))}
        </Card>

        <Card title="Manual Marketing Spend">
          <Form
            form={form}
            layout="vertical"
            onFinish={(values) =>
              void createMarketingSpend({
                channel: values.channel,
                campaign_name: values.campaign_name || null,
                spend_amount: String(values.spend_amount),
                currency: 'RUB',
                notes: values.notes || null,
                period_start: values.period?.[0]?.toISOString?.() ?? new Date().toISOString(),
                period_end: values.period?.[1]?.toISOString?.() ?? new Date().toISOString(),
              })
                .then(() => {
                  message.success('Расход добавлен')
                  form.resetFields()
                  void load()
                })
                .catch((error) => message.error(extractApiErrorMessage(error, 'Не удалось добавить расход')))
            }
          >
            <Form.Item name="channel" label="Канал" rules={[{ required: true }]}>
              <Input placeholder="tg_ads / meta / yandex / influencers" />
            </Form.Item>
            <Form.Item name="campaign_name" label="Кампания">
              <Input placeholder="Опционально" />
            </Form.Item>
            <Form.Item name="spend_amount" label="Расход" rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: '100%' }} addonAfter="₽" />
            </Form.Item>
            <Form.Item name="period" label="Период" initialValue={[dayjs().startOf('month'), dayjs().endOf('month')]}>
              <RangePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="notes" label="Заметки">
              <Input.TextArea rows={2} />
            </Form.Item>
            <Button type="primary" htmlType="submit">Добавить расход</Button>
          </Form>
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--ag-muted)' }}>
            Всего расходов: {fmtMoney(spendTotal)}
          </div>
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card title="CAC by Channel">
          <Table
            rowKey="channel"
            pagination={false}
            size="small"
            dataSource={economics?.channel_cac ?? []}
            columns={[
              { title: 'Channel', dataIndex: 'channel' },
              { title: 'Spend', dataIndex: 'spend', render: (v: number) => fmtMoney(v) },
              { title: 'First paid', dataIndex: 'first_paid_users' },
              { title: 'CAC', dataIndex: 'cac', render: (v: number) => fmtMoney(v) },
            ]}
          />
        </Card>

        <Card title="Cohorts M1 / M3 / M6">
          <Table
            rowKey="cohort"
            pagination={false}
            size="small"
            dataSource={cohorts}
            columns={[
              { title: 'Cohort', dataIndex: 'cohort' },
              { title: 'Size', dataIndex: 'size' },
              { title: 'M1', dataIndex: 'm1', render: (v: number) => `${v}%` },
              { title: 'M3', dataIndex: 'm3', render: (v: number) => `${v}%` },
              { title: 'M6', dataIndex: 'm6', render: (v: number) => `${v}%` },
            ]}
          />
        </Card>
      </div>
    </>
  )
}
