import { useEffect, useState } from 'react'
import { Alert, Button, Card, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchOneTimeMonthly } from '@/api/metrics'
import type { OneTimeMonthRow } from '@/types/admin'
import { downloadAdminCsv } from '@/utils/downloadAdminCsv'
import { extractApiErrorMessage } from '@/utils/apiError'

const { Paragraph } = Typography

function MiniBars({ rows }: { rows: OneTimeMonthRow[] }) {
  if (!rows.length) return <div className="admin-empty" style={{ height: 80 }}>Нет данных</div>
  const max = Math.max(...rows.map((r) => r.revenue_rub), 1)
  return (
    <div className="ag-mrr-wrap">
      {rows.map((p) => {
        const h = Math.max(Math.round((p.revenue_rub / max) * 76), 2)
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

export function OneTimeSalesPage() {
  const [rows, setRows] = useState<OneTimeMonthRow[]>([])
  const [methodology, setMethodology] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchOneTimeMonthly({ months: 12 })
      .then((d) => {
        setRows(d.rows)
        setMethodology(d.methodology)
      })
      .catch((e) => message.error(extractApiErrorMessage(e, 'Ошибка загрузки')))
      .finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<OneTimeMonthRow> = [
    { title: 'Месяц', dataIndex: 'month' },
    { title: 'Заказов', dataIndex: 'orders_count' },
    {
      title: 'Выручка, ₽',
      dataIndex: 'revenue_rub',
      render: (v: number) => v.toLocaleString('ru-RU', { maximumFractionDigits: 2 }),
    },
    {
      title: 'AOV, ₽',
      dataIndex: 'aov_rub',
      render: (v: number) => v.toLocaleString('ru-RU', { maximumFractionDigits: 2 }),
    },
  ]

  return (
    <>
      <Alert type="info" showIcon style={{ marginBottom: 16 }} message={methodology} />
      <Card
        style={{ marginBottom: 16 }}
        title="Выручка one-time по месяцам"
        extra={
          <Button
            size="small"
            onClick={() =>
              void downloadAdminCsv(
                '/api/v1/admin/export/orders.csv',
                'orders-one-time.csv',
                { billing_type: 'one_time', excel_bom: 1 },
              )
            }
          >
            Серверный CSV (one_time)
          </Button>
        }
      >
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          Столбцы — сумма заказов paid+completed с тарифами <code>billing_type = one_time</code>.
        </Paragraph>
        <MiniBars rows={rows} />
      </Card>
      <Card title="Таблица">
        <Table<OneTimeMonthRow> rowKey="month" loading={loading} columns={columns} dataSource={rows} pagination={false} size="small" />
      </Card>
    </>
  )
}
