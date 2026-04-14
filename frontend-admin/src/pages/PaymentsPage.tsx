import { useEffect, useState } from 'react'
import { Button, Card, Input, Select, Space, Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchPayments } from '@/api/payments'
import type { AdminPaymentRow } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

export function PaymentsPage() {
  const [rows, setRows] = useState<AdminPaymentRow[]>([])
  const [status, setStatus] = useState<string>('')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

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

  const columns: ColumnsType<AdminPaymentRow> = [
    { title: 'ID заказа', dataIndex: 'order_id' },
    { title: 'Email', dataIndex: 'user_email' },
    { title: 'Тариф', dataIndex: 'tariff_name' },
    { title: 'Сумма', dataIndex: 'amount' },
    { title: 'Статус', dataIndex: 'status', render: (s) => <Tag color={s === 'paid' ? 'green' : s === 'failed' ? 'red' : 'default'}>{s}</Tag> },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, row) => (
        <Button size="small" onClick={() => message.info(`Откройте пользователя #${row.user_id} в разделе Users`)}>
          К пользователю
        </Button>
      ),
    },
  ]

  return (
    <>
      <Card>
        <Space className="admin-toolbar">
          <Input
            placeholder="ID заказа или email"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onPressEnter={load}
            style={{ width: 260 }}
          />
          <Select
            style={{ width: 180 }}
            value={status}
            onChange={setStatus}
            options={[
              { value: '', label: 'Все статусы' },
              { value: 'paid', label: 'paid' },
              { value: 'refunded', label: 'refunded' },
              { value: 'pending', label: 'pending' },
              { value: 'failed', label: 'failed' },
            ]}
          />
          <Button type="primary" onClick={load}>Обновить</Button>
        </Space>
      </Card>
      <Card>
        {err && <div className="admin-empty">{err}</div>}
        <Table rowKey="order_id" loading={loading} columns={columns} dataSource={rows} pagination={{ pageSize: 20 }} />
      </Card>
    </>
  )
}
