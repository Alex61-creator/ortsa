import { useEffect, useState } from 'react'
import { Button, Card, Select, message } from 'antd'
import { fetchTasks } from '@/api/tasks'
import type { AdminTaskRow } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

function statusTag(status: string) {
  switch (status) {
    case 'completed': return <span className="ag-tag ag-tag-green">completed</span>
    case 'running':   return <span className="ag-tag ag-tag-blue">running</span>
    case 'pending':   return <span className="ag-tag ag-tag-amber">pending</span>
    case 'failed':    return <span className="ag-tag ag-tag-red">failed</span>
    default:          return <span className="ag-tag ag-tag-gray">{status}</span>
  }
}

function queueTag(queue: string) {
  if (queue.includes('report')) return <span className="ag-tag ag-tag-purple">{queue}</span>
  if (queue.includes('celery')) return <span className="ag-tag ag-tag-teal">{queue}</span>
  return <span className="ag-tag ag-tag-gray">{queue}</span>
}

function fmtTime(iso: string) {
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

export function TasksPage() {
  const [rows, setRows]   = useState<AdminTaskRow[]>([])
  const [status, setStatus] = useState('all')
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    void fetchTasks()
      .then(setRows)
      .catch((e) => {
        setRows([])
        message.error(extractApiErrorMessage(e, 'Не удалось загрузить задачи'))
      })
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const filtered  = rows.filter((r) => status === 'all' || r.status === status)
  const completed = rows.filter((r) => r.status === 'completed').length
  const failed    = rows.filter((r) => r.status === 'failed').length
  const running   = rows.filter((r) => r.status === 'running').length
  const pending   = rows.filter((r) => r.status === 'pending').length

  return (
    <>
      {/* ── KPI row ── */}
      <div className="admin-metric-grid" style={{ marginBottom: 18 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Completed</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-success)' }}>{completed}</div>
          <div className="admin-metric-delta admin-metric-delta--up">успешно</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Running</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-primary)' }}>{running}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">в процессе</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Pending</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-warning)' }}>{pending}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">в очереди</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Failed</div>
          <div
            className="admin-metric-value"
            style={{ color: failed > 0 ? 'var(--ag-danger)' : 'var(--ag-success)' }}
          >
            {failed}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dn">с ошибкой</div>
        </div>
      </div>

      {/* ── Toolbar ── */}
      <Card style={{ marginBottom: 12 }}>
        <div className="admin-toolbar">
          <Select
            value={status}
            onChange={setStatus}
            size="small"
            style={{ width: 180 }}
            options={[
              { value: 'all',       label: 'Все статусы' },
              { value: 'running',   label: 'running' },
              { value: 'pending',   label: 'pending' },
              { value: 'completed', label: 'completed' },
              { value: 'failed',    label: 'failed' },
            ]}
          />
          <Button size="small" loading={loading} onClick={load}>Обновить</Button>
          <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--ag-muted)' }}>
            {filtered.length} / {rows.length}
          </span>
        </div>
      </Card>

      {/* ── Task list ── */}
      <Card bodyStyle={{ padding: '4px 0' }}>
        {filtered.length === 0 ? (
          <div className="admin-empty" style={{ margin: 16 }}>Задач не найдено</div>
        ) : (
          filtered.map((item) => (
            <div key={item.id} className="ag-task-row">
              <div style={{ flex: 1 }}>
                <div className="ag-task-name">{item.name}</div>
                <div className="ag-task-meta">
                  {queueTag(item.queue)}
                  <span style={{ marginLeft: 8 }}>{fmtTime(item.created_at)}</span>
                </div>
              </div>
              {statusTag(item.status)}
              {item.status === 'failed' && (
                <Button
                  size="small"
                  type="default"
                  onClick={() => message.success(`Retry для ${item.id} отправлен`)}
                >
                  Retry
                </Button>
              )}
            </div>
          ))
        )}
      </Card>
    </>
  )
}
