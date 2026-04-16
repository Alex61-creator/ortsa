import { useCallback, useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, DatePicker, Select, Space, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { type Dayjs } from 'dayjs'
import { fetchCampaignPerformance } from '@/api/metrics'
import { downloadAdminCsv } from '@/utils/downloadAdminCsv'
import type { CampaignPerformanceOut, CampaignPerformanceRow } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const { RangePicker } = DatePicker
const { Text, Paragraph } = Typography

export function CampaignAnalyticsPage() {
  const [range, setRange] = useState<[Dayjs, Dayjs]>(() => [
    dayjs().subtract(30, 'day').startOf('day'),
    dayjs().endOf('day'),
  ])
  const [groupBy, setGroupBy] = useState<'campaign' | 'source'>('campaign')
  const [billingSegment, setBillingSegment] = useState<'all' | 'one_time' | 'subscription'>('all')
  const [data, setData] = useState<CampaignPerformanceOut | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchCampaignPerformance({
        date_from: range[0].toISOString(),
        date_to: range[1].toISOString(),
        group_by: groupBy,
        billing_segment: billingSegment,
      })
      setData(res)
    } catch (e) {
      message.error(extractApiErrorMessage(e, 'Не удалось загрузить кампании'))
    } finally {
      setLoading(false)
    }
  }, [range, groupBy, billingSegment])

  useEffect(() => {
    void load()
  }, [load])

  const columns: ColumnsType<CampaignPerformanceRow> = useMemo(
    () => [
      {
        title: groupBy === 'campaign' ? 'Кампания (UTM)' : 'Канал',
        dataIndex: 'segment_key',
        key: 'segment_key',
        ellipsis: true,
      },
      {
        title: 'Регистрации',
        dataIndex: 'signups',
        width: 120,
        sorter: (a, b) => a.signups - b.signups,
      },
      {
        title: 'Первая оплата (users)',
        dataIndex: 'first_paid_users',
        width: 140,
        sorter: (a, b) => a.first_paid_users - b.first_paid_users,
      },
      {
        title: 'Выручка 1-й оплаты, ₽',
        dataIndex: 'first_paid_revenue_rub',
        width: 160,
        render: (v: number) => v.toLocaleString('ru-RU', { maximumFractionDigits: 2 }),
        sorter: (a, b) => a.first_paid_revenue_rub - b.first_paid_revenue_rub,
      },
      {
        title: 'Order completed',
        dataIndex: 'orders_completed',
        width: 130,
        sorter: (a, b) => a.orders_completed - b.orders_completed,
      },
      {
        title: 'CR1',
        dataIndex: 'cr1',
        width: 90,
        render: (v: number) => `${(v * 100).toFixed(1)}%`,
        sorter: (a, b) => a.cr1 - b.cr1,
      },
    ],
    [groupBy],
  )

  return (
    <>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap align="center" className="admin-toolbar">
          <RangePicker
            value={range}
            onChange={(v) => {
              if (v?.[0] && v[1]) setRange([v[0], v[1]])
            }}
          />
          <Select
            style={{ width: 200 }}
            value={groupBy}
            onChange={(v) => setGroupBy(v)}
            options={[
              { value: 'campaign', label: 'Группировка: UTM campaign' },
              { value: 'source', label: 'Группировка: source_channel' },
            ]}
          />
          <Select
            style={{ width: 240 }}
            value={billingSegment}
            onChange={(v) => setBillingSegment(v)}
            options={[
              { value: 'all', label: 'Все тарифы (события)' },
              { value: 'one_time', label: 'Только one-time заказы' },
              { value: 'subscription', label: 'Только subscription' },
            ]}
          />
          <Button type="primary" onClick={() => void load()} loading={loading}>
            Обновить
          </Button>
          <Button
            size="small"
            onClick={() =>
              void downloadAdminCsv('/api/v1/admin/export/campaign-performance.csv', 'campaigns.csv', {
                excel_bom: 1,
                group_by: groupBy,
                billing_segment: billingSegment,
                date_from: range[0].toISOString(),
                date_to: range[1].toISOString(),
              })
            }
          >
            Серверный CSV
          </Button>
        </Space>
      </Card>

      {data?.methodology ? (
        <Alert type="info" showIcon style={{ marginBottom: 16 }} message="Методология" description={data.methodology} />
      ) : null}

      <Card title="Витрина кампаний">
        <Paragraph type="secondary" style={{ marginBottom: 12, fontSize: 13 }}>
          Данные из <Text code>analytics_events</Text> за выбранный период. Выручка — сумма{' '}
          <Text code>amount</Text> у <Text code>first_purchase_completed</Text>.
        </Paragraph>
        <Table<CampaignPerformanceRow>
          rowKey={(r) => r.segment_key}
          loading={loading}
          columns={columns}
          dataSource={data?.rows ?? []}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          size="small"
        />
      </Card>
    </>
  )
}
