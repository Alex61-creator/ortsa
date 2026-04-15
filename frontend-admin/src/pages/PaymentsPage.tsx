import { useEffect, useState } from 'react'
import { Button, Card, DatePicker, Input, Select, Table, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchPayments } from '@/api/payments'
import type { AdminPaymentRow } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const { RangePicker } = DatePicker

function statusTag(status: string) {
  switch (status) {
    case 'paid':      return <span className="ag-tag ag-tag-green">paid</span>
    case 'refunded':  return <span className="ag-tag ag-tag-purple">refunded</span>
    case 'pending':   return <span className="ag-tag ag-tag-amber">pending</span>
    case 'failed':    return <span className="ag-tag ag-tag-red">failed</span>
    case 'canceled':  return <span className="ag-tag ag-tag-gray">canceled</span>
    default:          return <span className="ag-tag ag-tag-gray">{status}</span>
  }
}

function fmtAmt(amount: string) {
  const n = parseFloat(amount)
  return isNaN(n) ? amount : `${n.toLocaleString('ru-RU')} ₽`
}

export function PaymentsPage() {
  const [rows, setRows]       = useState<AdminPaymentRow[]>([])
  const [status, setStatus]   = useState<string>('')
  const [q, setQ]             = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr]         = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setErr(null)
    void fetchPayments({ status: status || undefined, q: q.trim() || undefined })
      .then(setRows)
      .catch((e) => {
        setRows([])
        setErr(extractApiErrorMessage(e, 'Не удалось загрузить платежи'))
      })
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const totalAmt = rows
    .filter((r) => r.status === 'paid')
    .reduce((acc, r) => acc + parseFloat(r.amount || '0'), 0)
  const refundAmt = rows
    .filter((r) => r.status === 'refunded')
    .reduce((acc, r) => acc + parseFloat(r.amount || '0'), 0)

  const columns: ColumnsType<AdminPaymentRow> = [
    {
      title: 'ID заказа',
      dataIndex: 'order_id',
      width: 90,
      render: (v: number) => (
        <span style={{ fontFamily: 'monospace', color: 'var(--ag-primary)' }}>#{v}</span>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'user_email',
      render: (v: string) => (
        <span style={{ fontSize: 12, color: 'var(--ag-text-2)' }}>{v}</span>
      ),
    },
    {
      title: 'Тариф',
      dataIndex: 'tariff_name',
      render: (v: string) => <span className="ag-tag ag-tag-blue">{v}</span>,
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      render: (v: string) => (
        <span style={{ fontWeight: 500 }}>{fmtAmt(v)}</span>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      render: (s: string) => statusTag(s),
    },
    {
      title: 'Дата',
      dataIndex: 'created_at',
      render: (t: string) =>
        new Date(t).toLocaleString('ru-RU', {
          day: '2-digit', month: '2-digit', year: '2-digit',
          hour: '2-digit', minute: '2-digit',
        }),
    },
    {
      title: '',
      key: 'actions',
      width: 110,
      render: (_, row) => (
        <Button
          size="small"
          type="link"
          style={{ padding: 0, fontSize: 12 }}
          onClick={() => message.info(`Откройте пользователя #${row.user_id} во вкладке Пользователи`)}
        >
          К пользователю →
        </Button>
      ),
    },
  ]

  return (
    <>
      {/* ── KPI row ── */}
      <div className="admin-metric-grid" style={{ marginBottom: 18 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Платежей всего</div>
          <div className="admin-metric-value">{rows.length}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">в выборке</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Оплачено</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-success)' }}>
            {rows.filter((r) => r.status === 'paid').length}
          </div>
          <div className="admin-metric-delta admin-metric-delta--up">paid</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Выручка (paid)</div>
          <div className="admin-metric-value" style={{ fontSize: 18 }}>
            {totalAmt.toLocaleString('ru-RU')} ₽
          </div>
          <div className="admin-metric-delta admin-metric-delta--up">за период</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Возвраты</div>
          <div
            className="admin-metric-value"
            style={{
              color: refundAmt > 0 ? 'var(--ag-danger)' : 'var(--ag-success)',
              fontSize: 18,
            }}
          >
            {refundAmt > 0 ? `−${refundAmt.toLocaleString('ru-RU')} ₽` : '0 ₽'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dn">refunded</div>
        </div>
      </div>

      {/* ── Toolbar ── */}
      <Card style={{ marginBottom: 12 }}>
        <div className="admin-toolbar">
          <Input
            placeholder="ID заказа или email"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onPressEnter={load}
            allowClear
            style={{ width: 260 }}
          />
          <Select
            style={{ width: 180 }}
            value={status}
            onChange={setStatus}
            options={[
              { value: '',          label: 'Все статусы' },
              { value: 'paid',      label: 'paid' },
              { value: 'refunded',  label: 'refunded' },
              { value: 'pending',   label: 'pending' },
              { value: 'failed',    label: 'failed' },
              { value: 'canceled',  label: 'canceled' },
            ]}
          />
          <RangePicker size="small" placeholder={['Дата от', 'Дата до']} />
          <Button type="primary" size="small" onClick={load}>Применить</Button>
        </div>
      </Card>

      {/* ── Table ── */}
      <Card>
        {err && <div className="admin-empty" style={{ marginBottom: 12 }}>{err}</div>}
        <Table
          rowKey="order_id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          size="small"
        />
      </Card>
    </>
  )
}
