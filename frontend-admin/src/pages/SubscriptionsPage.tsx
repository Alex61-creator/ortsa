import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Row, Statistic, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { Link } from 'react-router-dom'
import { fetchSubscriptionsList, fetchSubscriptionsOverview } from '@/api/metrics'
import type { SubscriptionExportRow, SubscriptionMonthRow } from '@/types/admin'
import { downloadAdminCsv } from '@/utils/downloadAdminCsv'
import { extractApiErrorMessage } from '@/utils/apiError'

const { Paragraph } = Typography

function RevBars({ rows }: { rows: SubscriptionMonthRow[] }) {
  if (!rows.length) return <div className="admin-empty" style={{ height: 80 }}>Нет данных</div>
  const max = Math.max(
    ...rows.map((r) => r.subscription_order_revenue_rub + r.renewal_revenue_rub),
    1,
  )
  return (
    <div className="ag-mrr-wrap">
      {rows.map((p) => {
        const total = p.subscription_order_revenue_rub + p.renewal_revenue_rub
        const h = Math.max(Math.round((total / max) * 76), 2)
        return (
          <div key={p.month} className="ag-mrr-col">
            <div className="ag-mrr-bar" style={{ height: h, background: 'var(--ag-primary)' }} />
            <span className="ag-mrr-lbl">{p.month}</span>
          </div>
        )
      })}
    </div>
  )
}

export function SubscriptionsPage() {
  const [overview, setOverview] = useState<Awaited<ReturnType<typeof fetchSubscriptionsOverview>> | null>(null)
  const [list, setList] = useState<SubscriptionExportRow[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchSubscriptionsOverview({ months: 12 }), fetchSubscriptionsList({ limit: 200 })])
      .then(([ov, li]) => {
        setOverview(ov)
        setList(li.rows)
      })
      .catch((e) => message.error(extractApiErrorMessage(e, 'Ошибка загрузки')))
      .finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<SubscriptionMonthRow> = [
    { title: 'Месяц', dataIndex: 'month' },
    { title: 'Новых подписок', dataIndex: 'new_subscriptions' },
    { title: 'Заказов (sub)', dataIndex: 'first_payment_orders' },
    {
      title: 'Выручка заказов, ₽',
      dataIndex: 'subscription_order_revenue_rub',
      render: (v: number) => v.toLocaleString('ru-RU', { maximumFractionDigits: 2 }),
    },
    {
      title: 'Продления (события), ₽',
      dataIndex: 'renewal_revenue_rub',
      render: (v: number) => v.toLocaleString('ru-RU', { maximumFractionDigits: 2 }),
    },
  ]

  const listColumns: ColumnsType<SubscriptionExportRow> = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    {
      title: 'User',
      dataIndex: 'user_id',
      render: (uid: number) => (
        <Link to="/users">{uid}</Link>
      ),
    },
    { title: 'Тариф', dataIndex: 'tariff_code' },
    { title: 'Статус', dataIndex: 'status' },
    { title: 'Период с', dataIndex: 'current_period_start', render: (t: string | null) => t ?? '—' },
    { title: 'Период по', dataIndex: 'current_period_end', render: (t: string | null) => t ?? '—' },
  ]

  return (
    <>
      {overview?.methodology ? <Alert type="info" showIcon style={{ marginBottom: 16 }} message={overview.methodology} /> : null}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="Активных подписок (сейчас)" value={overview?.active_subscriptions_now ?? 0} />
          </Card>
        </Col>
      </Row>
      <Card
        style={{ marginBottom: 16 }}
        title="Выручка подписок по месяцам"
        extra={
          <Button
            size="small"
            onClick={() => void downloadAdminCsv('/api/v1/admin/export/subscriptions.csv', 'subscriptions.csv', { excel_bom: 1 })}
          >
            CSV подписок
          </Button>
        }
      >
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          Детали по синастрии и квотам — в карточке пользователя:{' '}
          <Link to="/users">Пользователи</Link>.
        </Paragraph>
        <RevBars rows={overview?.monthly_rows ?? []} />
      </Card>
      <Card title="Месячная таблица" style={{ marginBottom: 16 }}>
        <Table<SubscriptionMonthRow>
          rowKey="month"
          loading={loading}
          columns={columns}
          dataSource={overview?.monthly_rows ?? []}
          pagination={false}
          size="small"
        />
      </Card>
      <Card title="Последние подписки">
        <Table<SubscriptionExportRow>
          rowKey="id"
          loading={loading}
          columns={listColumns}
          dataSource={list}
          pagination={{ pageSize: 15 }}
          size="small"
        />
      </Card>
    </>
  )
}
