import { useEffect, useState } from 'react'
import { Button, Card, Spin } from 'antd'
import { fetchHealthWidgets } from '@/api/health'
import type { HealthWidget } from '@/types/admin'

function Dot({ status }: { status: string }) {
  const cls =
    status === 'ok'      ? 'ag-dot-green' :
    status === 'warn'    ? 'ag-dot-amber' :
                           'ag-dot-red'
  return <span className={`ag-dot ${cls}`} />
}

function statusTag(status: string) {
  if (status === 'ok')   return <span className="ag-tag ag-tag-green">OK</span>
  if (status === 'warn') return <span className="ag-tag ag-tag-amber">WARN</span>
  return <span className="ag-tag ag-tag-red">ERROR</span>
}

const MOCK_INCIDENTS = [
  { id: 'INC-041', title: 'payments.retry.timeout', severity: 'high',   time: '13 апр 22:14' },
  { id: 'INC-038', title: 'llm.generation.slow',    severity: 'medium', time: '11 апр 09:30' },
  { id: 'INC-035', title: 'smtp.delivery.fail',      severity: 'low',   time: '07 апр 17:55' },
]

function incidentTag(severity: string) {
  if (severity === 'high')   return <span className="ag-tag ag-tag-red">high</span>
  if (severity === 'medium') return <span className="ag-tag ag-tag-amber">medium</span>
  return <span className="ag-tag ag-tag-gray">low</span>
}

export function HealthPage() {
  const [rows, setRows]     = useState<HealthWidget[]>([])
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    void fetchHealthWidgets()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const okCount    = rows.filter((r) => r.status === 'ok').length
  const warnCount  = rows.filter((r) => r.status === 'warn').length
  const errCount   = rows.filter((r) => r.status !== 'ok' && r.status !== 'warn').length

  return (
    <Spin spinning={loading}>
      {/* ── KPI row ── */}
      <div className="admin-metric-grid" style={{ marginBottom: 18 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Здоровых сервисов</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-success)' }}>{okCount}</div>
          <div className="admin-metric-delta admin-metric-delta--up">из {rows.length} всего</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Предупреждений</div>
          <div
            className="admin-metric-value"
            style={{ color: warnCount > 0 ? 'var(--ag-warning)' : 'var(--ag-success)' }}
          >
            {warnCount}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">warn</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Ошибок</div>
          <div
            className="admin-metric-value"
            style={{ color: errCount > 0 ? 'var(--ag-danger)' : 'var(--ag-success)' }}
          >
            {errCount}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">недоступных</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Инцидентов</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-muted)' }}>
            —
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">
            <span className="ag-tag ag-tag-amber" style={{ fontSize: 9 }}>DEMO</span>
          </div>
        </div>
      </div>

      {/* ── Service grid ── */}
      <Card
        title="Статус сервисов"
        extra={
          <Button size="small" onClick={load}>
            Обновить
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        {rows.length === 0 ? (
          <div className="admin-empty">Загрузка…</div>
        ) : (
          <div className="ag-health-grid">
            {rows.map((row) => (
              <div key={row.name} className="ag-health-card">
                <div className="ag-health-name">
                  <Dot status={row.status} />
                  {row.name}
                  <span style={{ marginLeft: 'auto' }}>{statusTag(row.status)}</span>
                </div>
                <div
                  className="ag-health-val"
                  style={{
                    color:
                      row.status === 'ok'
                        ? 'var(--ag-text)'
                        : row.status === 'warn'
                        ? 'var(--ag-warning)'
                        : 'var(--ag-danger)',
                  }}
                >
                  {row.status === 'ok' ? row.value : 'НЕДОСТУПЕН'}
                </div>
                {row.status === 'ok' && (
                  <div className="ag-health-sub">{row.value}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ── Recent incidents ── */}
      <Card
        title="Последние инциденты"
        extra={
          <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span className="ag-tag ag-tag-amber" style={{ fontSize: 10 }}>DEMO · Sentry не подключён</span>
          </span>
        }
      >
        <div>
          {MOCK_INCIDENTS.map((inc) => (
            <div
              key={inc.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '10px 0',
                borderBottom: '1px solid var(--ag-border)',
              }}
            >
              <span
                style={{
                  fontSize: 11,
                  color: 'var(--ag-text-4)',
                  width: 60,
                  flexShrink: 0,
                  fontFamily: 'monospace',
                }}
              >
                {inc.id}
              </span>
              <span style={{ flex: 1, fontSize: 13, color: 'var(--ag-text)' }}>
                {inc.title}
              </span>
              <span style={{ fontSize: 11, color: 'var(--ag-muted)', width: 100, textAlign: 'right' }}>
                {inc.time}
              </span>
              {incidentTag(inc.severity)}
              <button
                style={{
                  background: 'none',
                  border: '1px solid var(--ag-border)',
                  borderRadius: 'var(--ag-r)',
                  fontSize: 11,
                  padding: '2px 10px',
                  cursor: 'pointer',
                  color: 'var(--ag-text-2)',
                }}
                onClick={() => alert(`Инцидент ${inc.id} отмечен как решённый`)}
              >
                Решено
              </button>
            </div>
          ))}
          <div style={{ paddingTop: 12 }}>
            <div className="admin-info-notice">
              📌 Для реального трекинга инцидентов подключите Sentry DSN в настройках.
            </div>
          </div>
        </div>
      </Card>
    </Spin>
  )
}
