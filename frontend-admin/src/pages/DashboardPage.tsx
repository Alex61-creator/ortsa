import { useEffect, useState } from 'react'
import { Card, Spin } from 'antd'
import { fetchDashboardSummary } from '@/api/dashboard'
import { fetchFunnelSummary } from '@/api/funnel'
import { fetchHealthWidgets } from '@/api/health'
import type { DashboardSummary, FunnelSummary, HealthWidget, MrrPoint } from '@/types/admin'

/* ─── helpers ─── */
const fmt = (n: number | undefined, symbol = '₽') =>
  n === undefined ? '—' : `${n.toLocaleString('ru-RU')} ${symbol}`

const FUNNEL_COLORS = ['#1677FF', '#4096FF', '#722ED1', '#EB2F96', '#52C41A']
const SRC_DATA = [
  { name: 'Прямые',   cnt: 112, color: '#1677FF' },
  { name: 'Telegram', cnt: 74,  color: '#2AABEE' },
  { name: 'Google',   cnt: 38,  color: '#34A853' },
  { name: 'ВКонтакте',cnt: 15,  color: '#2787F5' },
  { name: 'Прочие',   cnt: 8,   color: '#D9D9D9' },
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

/* ─── TRAFFIC SOURCES ─── */
function SourcesChart() {
  const max = SRC_DATA[0].cnt
  return (
    <>
      {SRC_DATA.map((s) => (
        <div key={s.name} className="ag-src-row">
          <div className="ag-src-name">{s.name}</div>
          <div className="ag-src-bar-w">
            <div
              className="ag-src-bar"
              style={{ width: `${Math.round((s.cnt / max) * 100)}%`, background: s.color }}
            />
          </div>
          <div className="ag-src-cnt">{s.cnt}</div>
        </div>
      ))}
      <div className="admin-info-notice">
        📌 После подключения UTM-меток появится разбивка по рекламным кампаниям.
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

/* ─── ROI BY PLAN ─── */
function RoiByPlan({ mrr, llmCost }: { mrr: number; llmCost: number }) {
  const plans = [
    { name: 'Astro Pro',  rev: mrr * 0.55, cost: llmCost * 0.6  },
    { name: 'Отчёт',      rev: mrr * 0.3,  cost: llmCost * 0.3  },
    { name: 'Набор «3»',  rev: mrr * 0.15, cost: llmCost * 0.1  },
  ]
  return (
    <>
      {plans.map((p) => {
        const roi = p.cost > 0 ? Math.round(((p.rev - p.cost) / p.cost) * 100) : 0
        return (
          <div key={p.name} className="ag-roi-row">
            <span style={{ fontSize: 13 }}>{p.name}</span>
            <span style={{ fontSize: 12, color: 'var(--ag-muted)' }}>
              {p.rev.toFixed(0)} ₽ / {p.cost.toFixed(0)} ₽
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

/* ═══════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════ */
export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [funnel, setFunnel] = useState<FunnelSummary | null>(null)
  const [health, setHealth] = useState<HealthWidget[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.allSettled([
      fetchDashboardSummary().then(setSummary),
      fetchFunnelSummary('current_month').then(setFunnel).catch(() => null),
      fetchHealthWidgets().then(setHealth).catch(() => []),
    ]).finally(() => setLoading(false))
  }, [])

  const bm = summary?.business_metrics
  const lm = summary?.llm_metrics
  const mrr = bm?.mrr ?? 0
  const llmCost = lm?.llm_cost ?? 0
  const mrrHistory = summary?.mrr_history ?? []

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
          <div className="admin-metric-label">MRR</div>
          <div className="admin-metric-value">{bm ? fmt(bm.mrr) : '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--up">↑ +{bm ? fmt(bm.new_mrr) : '—'} new</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">New MRR</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-success)' }}>
            +{bm ? fmt(bm.new_mrr) : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">новые подписки</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Churn MRR</div>
          <div className="admin-metric-value" style={{ color: 'var(--ag-danger)' }}>
            −{bm ? fmt(bm.churn_mrr) : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dn">возвраты</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Ср. LTV</div>
          <div className="admin-metric-value">{bm ? fmt(bm.ltv) : '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--up">↑ среднее</div>
        </div>
      </div>

      {/* ── Row 2: LLM / Ops KPIs ── */}
      <div className="admin-llm-grid">
        <div className="admin-metric-card">
          <div className="admin-metric-label">Затраты LLM</div>
          <div className="admin-metric-value">{lm ? fmt(lm.llm_cost, '$') : '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">GPT-4o · $/токен</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">ROI LLM</div>
          <div
            className="admin-metric-value"
            style={{ color: (lm?.roi_pct ?? 0) > 200 ? 'var(--ag-success)' : 'var(--ag-warning)' }}
          >
            {lm?.roi_pct ?? '—'}%
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">выручка / затраты</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Ср. цена отчёта</div>
          <div className="admin-metric-value">{lm ? fmt(lm.avg_report_cost, '$') : '—'}</div>
          <div className="admin-metric-delta admin-metric-delta--dim">на один отчёт</div>
        </div>
        <div className="admin-metric-card">
          <div className="admin-metric-label">Токенов всего</div>
          <div className="admin-metric-value">
            {lm ? (lm.tokens_total / 1000).toFixed(1) + 'k' : '—'}
          </div>
          <div className="admin-metric-delta admin-metric-delta--dim">за период</div>
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
            <span className="ag-tag ag-tag-amber" style={{ fontSize: 10 }}>
              DEMO · UTM в разработке
            </span>
          }
        >
          <SourcesChart />
        </Card>
        <Card
          title="Затраты LLM по месяцам"
          extra={
            <span style={{ fontSize: 11, color: 'var(--ag-muted)' }}>GPT-4o · $/токен × курс</span>
          }
        >
          {mrrHistory.length > 0 ? (
            <div className="ag-mrr-wrap">
              {mrrHistory.map((p) => {
                const cost = p.mrr * 0.18
                const max = Math.max(...mrrHistory.map((x) => x.mrr * 0.18), 1)
                const h = Math.max(Math.round((cost / max) * 76), 2)
                return (
                  <div key={p.month} className="ag-mrr-col">
                    <div className="ag-mrr-bar" style={{ height: h, background: 'var(--ag-warning)' }} />
                    <span className="ag-mrr-lbl">{p.month}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="admin-empty">Нет данных</div>
          )}
        </Card>
      </div>

      {/* ── Row 5: Health + ROI ── */}
      <div className="admin-two-col">
        <Card title="Статус системы">
          <HealthMini rows={health} />
        </Card>
        <Card
          title="ROI по тарифам"
          extra={
            <span style={{ fontSize: 11, color: 'var(--ag-muted)' }}>Выручка / затраты LLM</span>
          }
        >
          <RoiByPlan mrr={mrr} llmCost={llmCost} />
        </Card>
      </div>
    </Spin>
  )
}
