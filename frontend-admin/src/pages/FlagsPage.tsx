import { useEffect, useState } from 'react'
import { Card, Switch, message } from 'antd'
import { fetchFlags, patchFlag } from '@/api/flags'
import type { FeatureFlagRow } from '@/types/admin'

export function FlagsPage() {
  const [rows, setRows]     = useState<FeatureFlagRow[]>([])
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    void fetchFlags()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const enabled  = rows.filter((r) => r.enabled).length
  const disabled = rows.filter((r) => !r.enabled).length

  return (
    <>
      {/* ── KPI row ── */}
      <div className="admin-metric-grid" style={{ marginBottom: 18 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Всего флагов</div>
          <div className="admin-metric-value">{rows.length}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">в системе</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Включено</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-success)' }}>{enabled}</div>
          <div className="admin-metric-delta admin-metric-delta--up">активных</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Выключено</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-muted)' }}>{disabled}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">отключённых</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Статус</div>
          <div
            className="admin-metric-value"
            style={{ color: rows.length > 0 ? 'var(--ag-success)' : 'var(--ag-muted)' }}
          >
            {rows.length > 0 ? 'OK' : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">Redis cache</div>
        </div>
      </div>

      <Card
        title="Feature Flags"
        extra={
          <span style={{ fontSize: 11, color: 'var(--ag-muted)' }}>
            Изменения применяются мгновенно
          </span>
        }
        bodyStyle={{ padding: 0 }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '180px 1fr auto',
            gap: 8,
            padding: '8px 20px',
            background: 'var(--ag-card-soft)',
            borderBottom: '1px solid var(--ag-border)',
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--ag-muted)',
            textTransform: 'uppercase',
            letterSpacing: '.05em',
          }}
        >
          <span>Ключ</span>
          <span>Описание</span>
          <span>Вкл</span>
        </div>

        {loading ? (
          <div className="admin-empty" style={{ margin: 20 }}>Загрузка…</div>
        ) : rows.length === 0 ? (
          <div className="admin-empty" style={{ margin: 20 }}>Флаги не найдены</div>
        ) : (
          <div style={{ padding: '0 20px' }}>
            {rows.map((row) => (
              <div key={row.key} className="ag-flag-row">
                <div style={{ width: 180, flexShrink: 0 }}>
                  <div className="ag-flag-name" style={{ fontFamily: 'monospace', fontSize: 12 }}>
                    {row.key}
                  </div>
                  {row.enabled
                    ? <span className="ag-tag ag-tag-green" style={{ marginTop: 3 }}>enabled</span>
                    : <span className="ag-tag ag-tag-gray" style={{ marginTop: 3 }}>disabled</span>}
                </div>
                <div style={{ flex: 1 }}>
                  <div className="ag-flag-desc">{row.description || '—'}</div>
                </div>
                <Switch
                  checked={row.enabled}
                  onChange={(v) =>
                    void patchFlag(row.key, v)
                      .then(() => {
                        message.success(`${row.key} → ${v ? 'включён' : 'выключен'}`)
                        load()
                      })
                      .catch(() => message.error('Не удалось обновить флаг'))
                  }
                />
              </div>
            ))}
          </div>
        )}
      </Card>
    </>
  )
}
