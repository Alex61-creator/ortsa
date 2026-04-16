import { useEffect, useState } from 'react'
import { Card, Spin } from 'antd'
import { fetchDashboardSummary } from '@/api/dashboard'
import { fetchFunnelSummary } from '@/api/funnel'
import { fetchHealthWidgets } from '@/api/health'
import { fetchCampaignPerformance } from '@/api/metrics'
import type { DashboardSummary, FunnelSummary, HealthWidget, MonthAmountPoint, MrrPoint, TariffKpiRow } from '@/types/admin'

/* ─── helpers ─── */
const fmt = (n: number | undefined, symbol = '₽') =>
  n === undefined ? '—' : `${n.toLocaleString('ru-RU')} ${symbol}`

const FUNNEL_COLORS = ['#1677FF', '#4096FF', '#722ED1', '#EB2F96', '#52C41A']
const SOURCE_BAR_COLORS = [
  'var(--ag-primary)',
  'var(--ag-info)',
  'var(--ag-success)',
  'var(--ag-warning)',
  '#2AABEE',
]

/* ─── STATUS DOT ─── */
function Dot({ ok }: { ok: boolean }) {
  return <span className={`ag-dot ${ok ? 'ag-dot-green' : 'ag-dot-red'}`} />
}

/* ─── MRR MINI CHART ─── */
function MrrChart({ points }: { points: MrrPoint[] }) {
  if (!points.length) return <div className="admin-empty" style={{ height: 80 }}>Нет данных</div>
  const max = Math.max(...points.map((p) => p.mrr), 1)
  return (
    <>
      <div className="ag-mrr-wrap">
        {points.map((p) => {
          const h = Math.max(Math.round((p.mrr / max) * 76), 2)
          return (
            <div key={p.month} className="ag-mrr-col">
              <div className="ag-mrr-bar" style={{ height: h, background: 'var(--ag-primary)' }} />
              <span className="ag-mrr-lbl">{p.month}</span>
            </div>
          )
        })}
      </div>
      <div className="ag-mrr-legend">
        <div className="ag-mrr-legend-item">
          <span className="ag-mrr-legend-dot" style={{ background: 'var(--ag-primary)' }} />
          Доход
        </div>
      </div>
    </>
  )
}

/* ─── FUNNEL MINI ─── */
function FunnelMini({ data }: { data: FunnelSummary | null }) {
  if (!data || !data.steps.length)
    return <div className="admin-empty" style={{ minHeight: 100 }}>Загрузка…</div>
  const max = data.steps[0]?.count || 1
  return (
    <div className="ag-funnel-wrap">
      {data.steps.map((step, i) => {
        const pct = Math.round((step.count / max) * 100)
        const conv = i > 0 ? step.conversion_pct : null
        const col = conv !== null ? (conv < 50 ? 'var(--ag-danger)' : conv < 70 ? 'var(--ag-warning)' : 'var(--ag-success)') : 'var(--ag-muted)'
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
                style={{ width: `${pct}%`, background: FUNNEL_COLORS[i % FUNNEL_COLORS.length] }}
              >
                {step.count.toLocaleString()}
              </div>
            </div>
            <div className="ag-funnel-conv" style={{ color: col }}>
              {conv !== null ? `${conv.toFixed(1)}%` : '—'}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ─── TRAFFIC SOURCES (source_channel из событий, 30 дней) ─── */
function SourcesChart({
  rows,
}: {
  rows: { name: string; signups: number; revenue: number; color: string }[]
}) {
  if (!rows.length) {
    return <div className="admin-empty" style={{ minHeight: 80 }}>Нет событий signup за период</div>
  }
  const max = Math.max(...rows.map((s) => s.signups), 1)
  return (
    <>
      {rows.map((s) => (
        <div key={s.name} className="ag-src-row">
          <div className="ag-src-name" title={`Выручка 1-й оплаты: ${s.revenue.toLocaleString('ru-RU')} ₽`}>
            {s.name}
          </div>
          <div className="ag-src-bar-w">
            <div
              className="ag-src-bar"
              style={{ width: `${Math.round((s.signups / max) * 100)}%`, background: s.color }}
            />
          </div>
          <div className="ag-src-cnt">{s.signups}</div>
        </div>
      ))}
      <div className="admin-info-notice">
        Регистрации по <code>source_channel</code> (последние 30 дней). Полная витрина: раздел «Кампании и UTM».
      </div>
    </>
  )
}

/* ─── HEALTH MINI ─── */
function HealthMini({ rows }: { rows: HealthWidget[] }) {
  return (
    <>
      {rows.map((h) => (
        <div
          key={h.name}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 0',
            borderBottom: '1px solid var(--ag-border)',
          }}
        >
          <Dot ok={h.status === 'ok'} />
          <span style={{ flex: 1, fontSize: 13, color: 'var(--ag-text-2)' }}>{h.name}</span>
          <span
            style={{
              fontSize: 12,
              color: h.status === 'ok' ? 'var(--ag-muted)' : 'var(--ag-danger)',
            }}
          >
            {h.status === 'ok' ? h.value : 'НЕДОСТУПЕН'}
          </span>
        </div>
      ))}
    </>
  )
}

/* ─── Выручка и AI по тарифам (из заказов) ─── */
function TariffKpiBlock({ rows }: { rows: TariffKpiRow[] }) {
  if (!rows.length) {
    return <div className="admin-empty" style={{ minHeight: 80 }}>Нет оплаченных заказов</div>
  }
  return (
    <>
      {rows.map((p) => {
        const roi = p.ai_cost_rub > 0 ? Math.round(((p.revenue_rub - p.ai_cost_rub) / p.ai_cost_rub) * 100) : 0
        return (
          <div key={p.tariff_code} className="ag-roi-row">
            <span style={{ fontSize: 13 }}>{p.tariff_name}</span>
            <span style={{ fontSize: 12, color: 'var(--ag-muted)' }}>
              {p.revenue_rub.toFixed(0)} ₽ / AI {p.ai_cost_rub.toFixed(0)} ₽
            </span>
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: roi > 300 ? 'var(--ag-success)' : roi > 100 ? 'var(--ag-primary)' : 'var(--ag-warning)',
              }}
            >
              {roi}%
            </span>
          </div>
        )
      })}
    </>
  )
}

function AiCostChart({ points }: { points: MonthAmountPoint[] }) {
  if (!points.length) return <div className="admin-empty" style={{ height: 80 }}>Нет данных</div>
  const max = Math.max(...points.map((p) => p.amount_rub), 1)
  return (
    <>
      <div className="ag-mrr-wrap">
        {points.map((p) => {
          const h = Math.max(Math.round((p.amount_rub / max) * 76), 2)
          return (
            <div key={p.month} className="ag-mrr-col">
              <div className="ag-mrr-bar" style={{ height: h, background: 'var(--ag-warning)' }} />
              <span className="ag-mrr-lbl">{p.month}</span>
            </div>
          )
        })}
      </div>
      <div className="ag-mrr-legend">
        <div className="ag-mrr-legend-item">
          <span className="ag-mrr-legend-dot" style={{ background: 'var(--ag-warning)' }} />
          Затраты AI (₽)
        </div>
      </div>
    </>
  )
}

/* ═══════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════ */
export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [funnel, setFunnel] = useState<FunnelSummary | null>(null)
  const [health, setHealth] = useState<HealthWidget[]>([])
  const [trafficRows, setTrafficRows] = useState<
    { name: string; signups: number; revenue: number; color: string }[]
  >([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 30)
    Promise.allSettled([
      fetchDashboardSummary().then(setSummary),
      fetchFunnelSummary('current_month').then(setFunnel).catch(() => null),
      fetchHealthWidgets().then(setHealth).catch(() => []),
      fetchCampaignPerformance({
        date_from: start.toISOString(),
        date_to: end.toISOString(),
        group_by: 'source',
        billing_segment: 'all',
      })
        .then((camp) => {
          const top = [...camp.rows]
            .sort((a, b) => b.signups - a.signups)
            .slice(0, 6)
          setTrafficRows(
            top.map((r, i) => ({
              name: r.segment_key,
              signups: r.signups,
              revenue: r.first_paid_revenue_rub,
              color: SOURCE_BAR_COLORS[i % SOURCE_BAR_COLORS.length],
            })),
          )
        })
        .catch(() => setTrafficRows([])),
    ]).finally(() => setLoading(false))
  }, [])

  const bm = summary?.business_metrics
  const lm = summary?.llm_metrics
  const mrrHistory = summary?.mrr_history ?? []
  const aiCostHistory = summary?.ai_cost_history ?? []
  const tariffKpis = summary?.tariff_kpis ?? []

  return (
    <Spin spinning={loading}>
      {/* ── Row 1: Business KPIs ── */}
      <div className="admin-kpi-grid">
        <div className="admin-metric-card">
          <div className="admin-metric-label">Пользователи</div>
          <div className="admin-metric-value">{bm?.users_total ?? '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--up">↑ всего активных</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Выручка (paid+completed)</div>
          <div className="admin-metric-value">{bm ? fmt(bm.mrr) : '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">все время</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Выручка 30 дней</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-success)' }}>
            {bm ? fmt(bm.new_mrr) : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">те же статусы заказов</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Возвраты 30 дней</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-danger)' }}>
            {bm ? fmt(bm.churn_mrr) : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dn">sum(refunded_amount)</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Ср. выручка / пользователя</div>
          <div className="admin-metric-value">{bm ? fmt(bm.ltv) : '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">lifetime выручка / users</div>
        </div>
      </div>

      {/* ── Row 2: LLM / Ops KPIs ── */}
      <div className="admin-llm-grid">
        <div className="admin-metric-card">
          <div className="admin-metric-label">Затраты AI (заказы)</div>
          <div className="admin-metric-value">{lm ? fmt(lm.llm_cost) : '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">sum(ai_cost_amount)</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Вклад (gross − переменные)</div>
          <div
            className="admin-metric-value"
            style={{ color: (lm?.contribution_margin_pct ?? 0) > 30 ? 'var(--ag-success)' : 'var(--ag-warning)' }}
          >
            {lm?.contribution_margin_pct != null ? `${lm.contribution_margin_pct.toFixed(1)}%` : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">доля в выручке</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Ср. AI на completed</div>
          <div className="admin-metric-value">{lm ? fmt(lm.avg_report_cost) : '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">ai_cost / completed</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">ROI к AI</div>
          <div className="admin-metric-value">
            {lm?.roi_pct != null ? `${lm.roi_pct.toFixed(0)}%` : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">(выручка − стек) / AI</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Failed заказов</div>
          <div
            className="admin-metric-value"
            style={{
              color:
                (summary?.order_metrics.failed_orders_total ?? 0) > 0
                  ? 'var(--ag-danger)'
                  : 'var(--ag-success)',
            }}
          >
            {summary?.order_metrics.failed_orders_total ?? '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">требуют проверки</div>
        </div>
      </div>

      {/* ── Row 3: MRR Chart + Funnel ── */}
      <div className="admin-two-col">
        <Card title="MRR по месяцам">
          <MrrChart points={mrrHistory} />
        </Card>
        <Card title={`Воронка (${funnel?.period ?? 'апрель'})`}>
          <FunnelMini data={funnel} />
        </Card>
      </div>

      {/* ── Row 4: Traffic Sources + LLM Costs ── */}
      <div className="admin-two-col">
        <Card
          title="Источники трафика"
          extra={
            <span style={{ fontSize: 11, color: 'var(--ag-muted)' }}>30 дней · signup_completed</span>
          }
        >
          <SourcesChart rows={trafficRows} />
        </Card>
        <Card
          title="Затраты AI по месяцам"
          extra={
            <span style={{ fontSize: 11, color: 'var(--ag-muted)' }}>Из поля ai_cost_amount</span>
          }
        >
          <AiCostChart points={aiCostHistory} />
        </Card>
      </div>

      {/* ── Row 5: Health + ROI ── */}
      <div className="admin-two-col">
        <Card title="Статус системы">
          <HealthMini rows={health} />
        </Card>
        <Card
          title="Выручка и AI по тарифам"
          extra={
            <span style={{ fontSize: 11, color: 'var(--ag-muted)' }}>Заказы paid / completed / refunded</span>
          }
        >
          <TariffKpiBlock rows={tariffKpis} />
        </Card>
      </div>
    </Spin>
  )
}
