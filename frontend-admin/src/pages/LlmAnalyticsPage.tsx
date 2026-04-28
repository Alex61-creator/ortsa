import { useEffect, useState } from 'react'
import { Card, Col, DatePicker, Row, Statistic, Table, Tag, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { fetchLlmUsage, fetchLlmMargin } from '@/api/metrics'
import type { LlmMarginOut, LlmMarginRow, LlmProviderUsageRow, LlmUsageOut } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const PROVIDER_COLORS: Record<string, string> = {
  claude: 'purple',
  grok: 'blue',
  deepseek: 'green',
}

function fmtRub(v: number) {
  return `${v.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ₽`
}

function fmtPct(v: number) {
  return `${v.toFixed(1)}%`
}

function ProviderTag({ provider }: { provider: string }) {
  return <Tag color={PROVIDER_COLORS[provider] ?? 'default'}>{provider}</Tag>
}

export function LlmAnalyticsPage() {
  const [usage, setUsage] = useState<LlmUsageOut | null>(null)
  const [margin, setMargin] = useState<LlmMarginOut | null>(null)
  const [loadingUsage, setLoadingUsage] = useState(false)
  const [loadingMargin, setLoadingMargin] = useState(false)
  const [dateRange, setDateRange] = useState<[string, string] | null>(null)

  const loadUsage = async (dateFrom?: string, dateTo?: string) => {
    setLoadingUsage(true)
    try {
      const data = await fetchLlmUsage({ date_from: dateFrom, date_to: dateTo })
      setUsage(data)
    } catch (e) {
      message.error(extractApiErrorMessage(e))
    } finally {
      setLoadingUsage(false)
    }
  }

  const loadMargin = async () => {
    setLoadingMargin(true)
    try {
      const data = await fetchLlmMargin()
      setMargin(data)
    } catch (e) {
      message.error(extractApiErrorMessage(e))
    } finally {
      setLoadingMargin(false)
    }
  }

  useEffect(() => {
    loadUsage()
    loadMargin()
  }, [])

  const handleDateChange = (dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    if (!dates || !dates[0] || !dates[1]) {
      setDateRange(null)
      loadUsage()
      return
    }
    const from = dates[0].toISOString()
    const to = dates[1].toISOString()
    setDateRange([from, to])
    loadUsage(from, to)
  }

  const usageCols = [
    {
      title: 'Провайдер',
      dataIndex: 'provider',
      render: (v: string) => <ProviderTag provider={v} />,
    },
    {
      title: 'Вызовов',
      dataIndex: 'calls_count',
      render: (v: number) => v.toLocaleString(),
      sorter: (a: LlmProviderUsageRow, b: LlmProviderUsageRow) => a.calls_count - b.calls_count,
    },
    {
      title: '% от всего',
      dataIndex: 'pct_of_total',
      render: (v: number) => fmtPct(v),
      sorter: (a: LlmProviderUsageRow, b: LlmProviderUsageRow) => a.pct_of_total - b.pct_of_total,
    },
    {
      title: 'Стоимость',
      dataIndex: 'cost_rub',
      render: (v: number) => fmtRub(v),
      sorter: (a: LlmProviderUsageRow, b: LlmProviderUsageRow) => a.cost_rub - b.cost_rub,
    },
    {
      title: 'Кешир. токены',
      dataIndex: 'cached_tokens',
      render: (v: number) => v.toLocaleString(),
      sorter: (a: LlmProviderUsageRow, b: LlmProviderUsageRow) => a.cached_tokens - b.cached_tokens,
    },
  ]

  const marginCols = [
    {
      title: 'Провайдер',
      dataIndex: 'provider',
      render: (v: string) => <ProviderTag provider={v} />,
    },
    {
      title: 'Выручка',
      dataIndex: 'revenue_rub',
      render: (v: number) => fmtRub(v),
    },
    {
      title: 'AI-расходы',
      dataIndex: 'ai_cost_rub',
      render: (v: number) => fmtRub(v),
    },
    {
      title: 'Маржа',
      dataIndex: 'margin_rub',
      render: (v: number) => (
        <span style={{ color: v >= 0 ? 'var(--ag-success)' : 'var(--ag-danger)' }}>
          {fmtRub(v)}
        </span>
      ),
    },
    {
      title: 'Маржа %',
      dataIndex: 'margin_pct',
      render: (v: number) => (
        <span style={{ color: v >= 0 ? 'var(--ag-success)' : 'var(--ag-danger)' }}>
          {fmtPct(v)}
        </span>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>LLM Аналитика</Title>

      {/* ── Сводные карточки ───────────────────────────────────────────── */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Всего вызовов"
              value={usage?.total_calls ?? 0}
              loading={loadingUsage}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Расходы на AI"
              value={usage?.total_cost_rub ?? 0}
              suffix="₽"
              precision={2}
              loading={loadingUsage}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Основной провайдер"
              value={usage?.most_used_provider ?? '—'}
              loading={loadingUsage}
              formatter={(v) => <Tag color={PROVIDER_COLORS[v as string] ?? 'default'}>{v}</Tag>}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Кешир. токены Claude"
              value={
                usage?.rows.find((r) => r.provider === 'claude')?.cached_tokens ?? 0
              }
              loading={loadingUsage}
            />
          </Card>
        </Col>
      </Row>

      {/* ── Использование по провайдерам ───────────────────────────────── */}
      <Card
        title="Использование по провайдерам"
        style={{ marginBottom: 24 }}
        extra={
          <RangePicker
            onChange={handleDateChange as never}
            defaultValue={[
              dayjs().startOf('month'),
              dayjs(),
            ]}
            format="DD.MM.YYYY"
          />
        }
      >
        <Table
          dataSource={usage?.rows ?? []}
          columns={usageCols}
          rowKey="provider"
          loading={loadingUsage}
          pagination={false}
          size="middle"
          summary={(rows) => {
            if (!rows.length) return null
            const totalCalls = rows.reduce((s, r) => s + r.calls_count, 0)
            const totalCost = rows.reduce((s, r) => s + r.cost_rub, 0)
            const totalCached = rows.reduce((s, r) => s + r.cached_tokens, 0)
            return (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0}><strong>Итого</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={1}><strong>{totalCalls.toLocaleString()}</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={2}><strong>100%</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={3}><strong>{fmtRub(totalCost)}</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={4}><strong>{totalCached.toLocaleString()}</strong></Table.Summary.Cell>
              </Table.Summary.Row>
            )
          }}
        />
      </Card>

      {/* ── Маржинальность ─────────────────────────────────────────────── */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="Маржинальность — текущий месяц" loading={loadingMargin}>
            <Table
              dataSource={margin?.current_month ?? []}
              columns={marginCols}
              rowKey="provider"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Маржинальность — всё время" loading={loadingMargin}>
            <Table
              dataSource={margin?.total ?? []}
              columns={marginCols}
              rowKey="provider"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 16 }}>
        <Text type="secondary">
          <strong>Кешированные токены</strong> — токены Claude, прочитанные из prompt cache (ephemeral).
          Экономия ~90% по сравнению с обычными input-токенами.
          Маржинальность рассчитывается как выручка от заказов (по llm_provider отчёта) минус прямые AI-расходы.
        </Text>
      </Card>
    </div>
  )
}
