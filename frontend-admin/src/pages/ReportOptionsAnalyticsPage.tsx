import { useEffect, useState } from 'react'
import { Alert, Card, Col, Row, Statistic, Typography, message } from 'antd'
import { fetchReportOptionsAnalytics } from '@/api/metrics'
import type { ReportOptionsAnalyticsOut } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const { Paragraph } = Typography

const KEY_ORDER = ['partnership', 'children_parenting', 'career', 'money_boundaries']

function BarList({
  title,
  entries,
}: {
  title: string
  entries: { label: string; value: number; color: string }[]
}) {
  const max = Math.max(...entries.map((e) => e.value), 1)
  return (
    <Card title={title} size="small" style={{ height: '100%' }}>
      {entries.map((e) => (
        <div key={e.label} style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 12, color: 'var(--ag-text-2)', marginBottom: 4 }}>{e.label}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 8, background: 'var(--ag-border)', borderRadius: 4 }}>
              <div
                style={{
                  width: `${Math.round((e.value / max) * 100)}%`,
                  height: 8,
                  borderRadius: 4,
                  background: e.color,
                }}
              />
            </div>
            <span style={{ fontSize: 12, minWidth: 32 }}>{e.value}</span>
          </div>
        </div>
      ))}
    </Card>
  )
}

export function ReportOptionsAnalyticsPage() {
  const [data, setData] = useState<ReportOptionsAnalyticsOut | null>(null)

  useEffect(() => {
    fetchReportOptionsAnalytics()
      .then(setData)
      .catch((e) => message.error(extractApiErrorMessage(e, 'Ошибка загрузки')))
  }, [])

  const keyEntries =
    data == null
      ? []
      : KEY_ORDER.map((k) => ({
          label: k,
          value: data.key_counts[k] ?? 0,
          color: 'var(--ag-primary)',
        }))

  const bucketEntries =
    data == null
      ? []
      : [0, 1, 2, 3, 4].map((n) => ({
          label: `${n} опций`,
          value: data.bucket_counts[String(n)] ?? 0,
          color: 'var(--ag-info)',
        }))

  return (
    <>
      {data?.methodology ? <Alert type="info" showIcon style={{ marginBottom: 16 }} message={data.methodology} /> : null}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="Оценка выручки опций, ₽" value={data?.estimated_options_revenue_rub ?? 0} precision={2} />
            <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>
              Заказов в выборке: {data?.orders_sampled ?? 0}
            </Paragraph>
          </Card>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col xs={24} md={12}>
          <BarList title="Популярность по ключу" entries={keyEntries} />
        </Col>
        <Col xs={24} md={12}>
          <BarList title="Распределение числа опций (0–4)" entries={bucketEntries} />
        </Col>
      </Row>
    </>
  )
}
