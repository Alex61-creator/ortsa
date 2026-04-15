import { useEffect, useState } from 'react'
import { Button, Card, Input, Select } from 'antd'
import { fetchAdminLogs } from '@/api/logs'
import type { AdminLogRow } from '@/types/admin'

function actionTag(action: string) {
  if (action.includes('refund'))  return <span className="ag-tag ag-tag-red">{action}</span>
  if (action.includes('block'))   return <span className="ag-tag ag-tag-amber">{action}</span>
  if (action.includes('delete'))  return <span className="ag-tag ag-tag-red">{action}</span>
  if (action.includes('create'))  return <span className="ag-tag ag-tag-green">{action}</span>
  if (action.includes('promo'))   return <span className="ag-tag ag-tag-purple">{action}</span>
  if (action.includes('email'))   return <span className="ag-tag ag-tag-teal">{action}</span>
  return <span className="ag-tag ag-tag-blue">{action}</span>
}

function fmtTime(iso: string) {
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function ActionLogPage() {
  const [rows, setRows]         = useState<AdminLogRow[]>([])
  const [q, setQ]               = useState('')
  const [actionType, setActionType] = useState('all')

  const load = () => void fetchAdminLogs().then(setRows).catch(() => setRows([]))
  useEffect(() => { load() }, [])

  const filtered = rows.filter((r) => {
    const matchQ = `${r.actor_email} ${r.action} ${r.entity}`
      .toLowerCase()
      .includes(q.trim().toLowerCase())
    const matchType = actionType === 'all' || r.action.includes(actionType)
    return matchQ && matchType
  })

  return (
    <>
      {/* ── Toolbar ── */}
      <Card style={{ marginBottom: 12 }}>
        <div className="admin-toolbar">
          <Input
            placeholder="Поиск по email / действию / сущности"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{ width: 300 }}
            allowClear
          />
          <Select
            value={actionType}
            onChange={setActionType}
            style={{ width: 180 }}
            options={[
              { value: 'all',    label: 'Все типы' },
              { value: 'refund', label: 'refund' },
              { value: 'block',  label: 'block' },
              { value: 'delete', label: 'delete' },
              { value: 'create', label: 'create' },
              { value: 'email',  label: 'email' },
              { value: 'promo',  label: 'promo' },
            ]}
          />
          <Button onClick={load}>Обновить</Button>
          <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--ag-muted)' }}>
            {filtered.length} записей
          </span>
        </div>
      </Card>

      {/* ── Log list ── */}
      <Card bodyStyle={{ padding: '4px 0' }}>
        {filtered.length === 0 ? (
          <div className="admin-empty" style={{ margin: 16 }}>Записей не найдено</div>
        ) : (
          filtered.map((row) => (
            <div key={row.id} className="ag-log-row">
              <div className="ag-log-time">{fmtTime(row.created_at)}</div>
              <div className="ag-log-who">{row.actor_email}</div>
              <div className="ag-log-action">
                {actionTag(row.action)}
                {row.entity && (
                  <span
                    style={{
                      marginLeft: 8,
                      fontSize: 11,
                      color: 'var(--ag-muted)',
                      fontFamily: 'monospace',
                    }}
                  >
                    {row.entity}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </Card>
    </>
  )
}
