import { useEffect, useState } from 'react'
import { Card, Select, Spin } from 'antd'
import { fetchFunnelSummary } from '@/api/funnel'
import type { FunnelSummary } from '@/types/admin'

const FUNNEL_COLORS = ['#1677FF', '#4096FF', '#722ED1', '#EB2F96', '#52C41A']

const PERIOD_OPTIONS = [
  { value: 'today',         label: 'Сегодня' },
  { value: 'current_week',  label: 'Эта неделя' },
  { value: 'current_month', label: 'Этот месяц' },
]

export function FunnelPage() {
  const [summary, setSummary]   = useState<FunnelSummary | null>(null)
  const [period, setPeriod]     = useState('current_month')
  const [loading, setLoading]   = useState(false)

  useEffect(() => {
    setLoading(true)
    void fetchFunnelSummary(period)
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false))
  }, [period])

  const max = summary?.steps[0]?.count || 1

  return (
    <Spin spinning={loading}>
      {/* ── KPI row ── */}
      <div className="admin-metric-grid" style={{ marginBottom: 18 }}>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Шагов в воронке</div>
          <div className="admin-metric-value">{summary?.steps.length ?? '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">этапов</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Вход</div>
          <div className="admin-metric-value">{summary?.steps[0]?.count.toLocaleString() ?? '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">уникальных визитов</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Конверсия</div>
          <div
            className="admin-metric-value"
            style={{
              color:
                (summary?.steps.at(-1)?.conversion_pct ?? 0) > 5
                  ? 'var(--ag-success)'
                  : 'var(--ag-warning)',
            }}
          >
            {summary?.steps.at(-1)
              ? `${summary.steps.at(-1)!.conversion_pct.toFixed(1)}%`
              : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">вход → оплата</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Отвалилось</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-danger)' }}>
            {summary
              ? (summary.steps[0].count - (summary.steps.at(-1)?.count ?? 0)).toLocaleString()
              : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dn">не дошли до оплаты</div>
        </div>
      </div>

      {/* ── Main funnel card ── */}
      <Card
        title={`Воронка продаж · ${summary?.period ?? '...'}`}
        extra={
          <Select
            value={period}
            onChange={setPeriod}
            size="small"
            style={{ width: 160 }}
            options={PERIOD_OPTIONS}
          />
        }
        style={{ marginBottom: 16 }}
      >
        {!summary || !summary.steps.length ? (
          <div className="admin-empty">Нет данных за выбранный период</div>
        ) : (
          <div className="ag-funnel-wrap">
            {summary.steps.map((step, i) => {
              const pct = Math.round((step.count / max) * 100)
              const conv = i > 0 ? step.conversion_pct : null
              const convColor =
                conv === null
                  ? 'var(--ag-muted)'
                  : conv < 50
                  ? 'var(--ag-danger)'
                  : conv < 70
                  ? 'var(--ag-warning)'
                  : 'var(--ag-success)'
              return (
                <div key={step.key} className="ag-funnel-row">
                  <div
                    className="ag-funnel-num"
                    style={{ background: FUNNEL_COLORS[i % FUNNEL_COLORS.length] }}
                  >
                    {i + 1}
                  </div>
                  <div className="ag-funnel-label">{step.title}</div>
                  <div className="ag-funnel-bar-w">
                    <div
                      className="ag-funnel-bar"
                      style={{
                        width: `${pct}%`,
                        background: FUNNEL_COLORS[i % FUNNEL_COLORS.length],
                      }}
                    >
                      {step.count.toLocaleString()}
                    </div>
                  </div>
                  <div className="ag-funnel-conv" style={{ color: convColor }}>
                    {conv !== null ? `${conv.toFixed(1)}%` : '—'}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {/* ── Drop-offs ── */}
      {!!summary?.drop_offs?.length && (
        <Card title="Отвалы по этапам" style={{ marginBottom: 16 }}>
          <div className="admin-three-col" style={{ marginBottom: 0 }}>
            {summary.drop_offs.map((d) => (
              <div key={`${d.from_key}-${d.to_key}`} className="admin-metric-card">
                <div className="admin-metric-label">{d.from_key} → {d.to_key}</div>
                <div className="admin-metric-value" style={{ color: 'var(--ag-danger)' }}>
                  −{d.lost.toLocaleString()}
                </div>
                <div className="admin-metric-delta admin-metric-delta--dn">потерянных</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── Recommendations ── */}
      {!!summary?.recommendations?.length && (
        <Card title="Рекомендации">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {summary.recommendations.map((rec, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: 10,
                  padding: '10px 12px',
                  background: 'var(--ag-primary-l)',
                  border: '1px solid var(--ag-primary-b)',
                  borderRadius: 'var(--ag-r)',
                  fontSize: 13,
                  color: 'var(--ag-text-2)',
                }}
              >
                <span style={{ color: 'var(--ag-primary)', fontWeight: 600, flexShrink: 0 }}>
                  {i + 1}.
                </span>
                {rec}
              </div>
            ))}
          </div>
        </Card>
      )}
    </Spin>
  )
}
