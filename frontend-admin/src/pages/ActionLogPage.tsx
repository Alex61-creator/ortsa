import { useEffect, useState } from 'react'
import { Button, Card, Input, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchAdminLogs } from '@/api/logs'
import type { AdminLogRow } from '@/types/admin'

export function ActionLogPage() {
  const [rows, setRows] = useState<AdminLogRow[]>([])
  const [q, setQ] = useState('')
  const [actionType, setActionType] = useState<string>('all')
  useEffect(() => { void fetchAdminLogs().then(setRows).catch(() => setRows([])) }, [])
  const filtered = rows.filter((r) =>
    `${r.actor_email} ${r.action} ${r.entity}`.toLowerCase().includes(q.trim().toLowerCase()) &&
    (actionType === 'all' ? true : r.action.includes(actionType))
  )

  const columns: ColumnsType<AdminLogRow> = [
    { title: 'Когда', dataIndex: 'created_at' },
    { title: 'Кто', dataIndex: 'actor_email' },
    {
      title: 'Действие',
      dataIndex: 'action',
      render: (v: string) => <Tag color={v.includes('refund') ? 'red' : v.includes('block') ? 'orange' : 'blue'}>{v}</Tag>,
    },
    { title: 'Сущность', dataIndex: 'entity' },
  ]

  return (
    <>
      <Card>
        <Space className="admin-toolbar">
          <Input
            placeholder="Поиск по email/действию"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ width: 280 }}
          />
          <Button onClick={() => void fetchAdminLogs().then(setRows)}>Обновить</Button>
          <Select
            value={actionType}
            onChange={setActionType}
            style={{ width: 180 }}
            options={[
              { value: 'all', label: 'Все типы' },
              { value: 'refund', label: 'refund' },
              { value: 'block', label: 'block' },
              { value: 'email', label: 'email' },
              { value: 'promo', label: 'promo' },
            ]}
          />
        </Space>
      </Card>
      <Card>
        <Table rowKey="id" columns={columns} dataSource={filtered} pagination={{ pageSize: 20 }} />
      </Card>
    </>
  )
}
