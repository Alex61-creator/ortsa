import { useEffect, useMemo, useState } from 'react'
import { Button, Card, DatePicker, Form, Input, InputNumber, Select, Table, Tag, message } from 'antd'
import dayjs from 'dayjs'
import { createMarketingSpend, fetchLlmMargin, fetchMarketingSpend, fetchMetricsCohorts, fetchMetricsEconomics, fetchMetricsFunnel, fetchMetricsOverview } from '@/api/metrics'
import type {
  CohortRow,
  FunnelStep,
  FunnelSummary,
  LlmMarginOut,
  LlmMarginRow,
  MarketingSpendRow,
  MetricsEconomicsOut,
  MetricsOverviewOut,
} from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const PROVIDER_COLORS: Record<string, string> = { claude: 'purple', grok: 'blue', deepseek: 'green' }

const { RangePicker } = DatePicker

function fmtMoney(value: number) {
  return `${value.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ₽`
}

function fmtPercent(value: number) {
  return `${(value * 100).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%`
}

const FUNNEL_COLORS = ['#1677FF', '#4096FF', '#722ED1', '#EB2F96', '#52C41A']

function heatCellPct(v: number) {
  const t = Math.min(100, Math.max(0, v)) / 100
  const bg = `rgba(109, 93, 251, ${0.08 + t * 0.42})`
  return (
    <div
      style={{
        background: bg,
        borderRadius: 8,
        padding: '6px 8px',
        fontWeight: 600,
        textAlign: 'center',
      }}
      aria-label={`retention ${v}%`}
    >
      {v}%
    </div>
  )
}

function GrowthFunnelMini({ data }: { data: FunnelSummary | null }) {
  if (!data || !data.steps.length) {
    return <div className="admin-empty" style={{ minHeight: 100 }}>Нет данных воронки</div>
  }
  const max = data.steps[0]?.count || 1
  return (
    <div className="ag-funnel-wrap">
      {data.steps.map((step: FunnelStep, i: number) => {
        const pct = Math.round((step.count / max) * 100)
        const conv = i > 0 ? step.conversion_pct : null
        const col =
          conv !== null
            ? (conv < 50 ? 'var(--ag-danger)' : conv < 70 ? 'var(--ag-warning)' : 'var(--ag-success)')
            : 'var(--ag-muted)'
        return (
          <div key={step.key} className="ag-funnel-row">
            <div
              className="ag-funnel-num"
              style={{ background: FUNNEL_COLORS[i % FUNNEL_COLORS.length] }}
            >
              {i + 1}
            </div>
            <div className="ag-funnel-label">{step.title}</div>
            <div className="ag-funnel-bar-w">
              <div
                className="ag-funnel-bar"
                style={{
                  width: `${pct}%`,
                  background: FUNNEL_COLORS[i % FUNNEL_COLORS.length],
                }}
              >
                {step.count.toLocaleString()}
              </div>
            </div>
            <div className="ag-funnel-conv" style={{ color: col }}>
              {conv !== null ? `${conv.toFixed(1)}%` : '—'}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function GrowthEconomicsPage() {
  const [period, setPeriod] = useState('current_month')
  const [overview, setOverview] = useState<MetricsOverviewOut | null>(null)
  const [economics, setEconomics] = useState<MetricsEconomicsOut | null>(null)
  const [cohorts, setCohorts] = useState<CohortRow[]>([])
  const [spendRows, setSpendRows] = useState<MarketingSpendRow[]>([])
  const [funnel, setFunnel] = useState<FunnelSummary | null>(null)
  const [llmMargin, setLlmMargin] = useState<LlmMarginOut | null>(null)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const [overviewData, economicsData, cohortData, spendData, funnelData, llmMarginData] = await Promise.all([
        fetchMetricsOverview({ period }),
        fetchMetricsEconomics({ period }),
        fetchMetricsCohorts({ period }),
        fetchMarketingSpend(),
        fetchMetricsFunnel({ period }),
        fetchLlmMargin(),
      ])
      setOverview(overviewData)
      setEconomics(economicsData)
      setCohorts(cohortData.rows)
      setSpendRows(spendData)
      setFunnel(funnelData)
      setLlmMargin(llmMarginData)
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

      <Card title="Воронка (event-based)" style={{ marginBottom: 16 }}>
        <GrowthFunnelMini data={funnel} />
      </Card>

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

        <Card title="Cohorts M1 / M3 / M6 (heatmap)">
          <Table
            rowKey="cohort"
            pagination={false}
            size="small"
            dataSource={cohorts}
            columns={[
              { title: 'Cohort', dataIndex: 'cohort' },
              { title: 'Size', dataIndex: 'size' },
              { title: 'M1', dataIndex: 'm1', render: (v: number) => heatCellPct(v) },
              { title: 'M3', dataIndex: 'm3', render: (v: number) => heatCellPct(v) },
              { title: 'M6', dataIndex: 'm6', render: (v: number) => heatCellPct(v) },
            ]}
          />
        </Card>

        {/* ── Маржинальность по LLM ───────────────────────────────────── */}
        <Card title="Маржинальность по LLM-провайдерам" style={{ marginTop: 16 }}>
          <Table
            rowKey="provider"
            pagination={false}
            size="small"
            dataSource={llmMargin?.current_month ?? []}
            loading={loading}
            columns={[
              {
                title: 'Провайдер',
                dataIndex: 'provider',
                render: (v: string) => <Tag color={PROVIDER_COLORS[v] ?? 'default'}>{v}</Tag>,
              },
              {
                title: 'Выручка',
                dataIndex: 'revenue_rub',
                render: (v: number) => fmtMoney(v),
              },
              {
                title: 'AI-расходы',
                dataIndex: 'ai_cost_rub',
                render: (v: number) => fmtMoney(v),
              },
              {
                title: 'Маржа',
                dataIndex: 'margin_rub',
                render: (v: number) => (
                  <span style={{ color: v >= 0 ? 'var(--ag-success, green)' : 'var(--ag-danger, red)' }}>
                    {fmtMoney(v)}
                  </span>
                ),
              },
              {
                title: 'Маржа %',
                dataIndex: 'margin_pct',
                render: (v: number) => (
                  <span style={{ color: v >= 0 ? 'var(--ag-success, green)' : 'var(--ag-danger, red)' }}>
                    {v.toFixed(1)}%
                  </span>
                ),
              },
            ]}
            summary={(rows) => {
              if (!rows.length) return null
              const totalRev = rows.reduce((s, r: LlmMarginRow) => s + r.revenue_rub, 0)
              const totalCost = rows.reduce((s, r: LlmMarginRow) => s + r.ai_cost_rub, 0)
              const totalMargin = totalRev - totalCost
              return (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}><strong>Итого</strong></Table.Summary.Cell>
                  <Table.Summary.Cell index={1}><strong>{fmtMoney(totalRev)}</strong></Table.Summary.Cell>
                  <Table.Summary.Cell index={2}><strong>{fmtMoney(totalCost)}</strong></Table.Summary.Cell>
                  <Table.Summary.Cell index={3}>
                    <strong style={{ color: totalMargin >= 0 ? 'green' : 'red' }}>
                      {fmtMoney(totalMargin)}
                    </strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={4}>
                    <strong style={{ color: totalMargin >= 0 ? 'green' : 'red' }}>
                      {totalRev > 0 ? ((totalMargin / totalRev) * 100).toFixed(1) : '0'}%
                    </strong>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              )
            }}
          />
        </Card>
      </div>
    </>
  )
}
