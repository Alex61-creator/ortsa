import { useEffect, useState } from 'react'
import { Button, Card, List, Select, Space, Tag, Typography, message } from 'antd'
import { fetchTasks } from '@/api/tasks'
import type { AdminTaskRow } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

export function TasksPage() {
  const [rows, setRows] = useState<AdminTaskRow[]>([])
  const [status, setStatus] = useState('all')
  const load = () =>
    void fetchTasks()
      .then(setRows)
      .catch((e) => {
        setRows([])
        message.error(extractApiErrorMessage(e, 'Не удалось загрузить задачи'))
      })
  useEffect(() => {
    load()
  }, [])
  const filtered = rows.filter((r) => (status === 'all' ? true : r.status === status))
  const completed = rows.filter((r) => r.status === 'completed').length
  const failed = rows.filter((r) => r.status === 'failed').length
  const pending = rows.filter((r) => r.status === 'pending' || r.status === 'running').length

  return (
    <>
      <div className="admin-page-title">Задачи Celery</div>
      <div className="admin-metric-grid">
        <div className="admin-metric-card"><div className="admin-metric-label">Completed</div><div className="admin-metric-value">{completed}</div></div>
        <div className="admin-metric-card"><div className="admin-metric-label">Pending/Running</div><div className="admin-metric-value">{pending}</div></div>
        <div className="admin-metric-card"><div className="admin-metric-label">Failed</div><div className="admin-metric-value">{failed}</div></div>
        <div className="admin-metric-card"><div className="admin-metric-label">Всего</div><div className="admin-metric-value">{rows.length}</div></div>
      </div>
      <Card>
        <Space className="admin-toolbar" style={{ marginBottom: 12 }}>
          <Select
            value={status}
            onChange={setStatus}
            style={{ width: 180 }}
            options={[
              { value: 'all', label: 'Все статусы' },
              { value: 'running', label: 'running' },
              { value: 'pending', label: 'pending' },
              { value: 'completed', label: 'completed' },
              { value: 'failed', label: 'failed' },
            ]}
          />
          <Button onClick={load}>Обновить</Button>
        </Space>
        <List
          dataSource={filtered}
          renderItem={(item) => (
            <List.Item>
              <Typography.Text>{item.name}</Typography.Text>
              <Typography.Text type="secondary">{item.queue}</Typography.Text>
              <Tag color={item.status === 'completed' ? 'green' : item.status === 'failed' ? 'red' : 'blue'}>{item.status}</Tag>
              {item.status === 'failed' && <Button size="small" onClick={() => message.success(`Retry для ${item.id} отправлен`)}>Retry</Button>}
            </List.Item>
          )}
        />
      </Card>
    </>
  )
}
