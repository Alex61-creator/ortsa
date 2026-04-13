import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { fetchDashboardSummary } from '@/api/dashboard'
import { Spin } from 'antd'

export function DashboardHomePage() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({ queryKey: ['dashboard-summary'], queryFn: fetchDashboardSummary })

  if (isLoading || !data) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin />
      </div>
    )
  }

  const sub = data.subscription
  const planLabel = sub ? sub.tariff_name : '—'
  const periodHint =
    sub?.current_period_end != null
      ? t('dashboard.homePlanUntil', { date: dayjs(sub.current_period_end).format('DD.MM') })
      : t('dashboard.homePlanHint')

  return (
    <div>
      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="stat-icon">☉</div>
          <div className="stat-val">{data.natal_count}</div>
          <div className="stat-label">{t('dashboard.homeStatNatal')}</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📄</div>
          <div className="stat-val">{data.reports_ready_count}</div>
          <div className="stat-label">{t('dashboard.homeStatReports')}</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✦</div>
          <div className="stat-val" style={{ fontSize: 22, color: 'var(--purple)' }}>
            {planLabel}
          </div>
          <div className="stat-label">{periodHint}</div>
        </div>
      </div>

      <div className="recent-row">
        <div className="card">
          <div className="card-header">
            <div className="card-title">{t('dashboard.homeRecentOrders')}</div>
            <Link to="/dashboard/orders" className="btn btn-ghost btn-sm">
              {t('dashboard.homeAllOrders')}
            </Link>
          </div>
          <div className="card-body" style={{ paddingTop: 12 }}>
            {data.recent_orders.length === 0 ? (
              <p style={{ color: 'var(--text-3)', fontSize: 14 }}>{t('dashboard.homeNoOrders')}</p>
            ) : (
              data.recent_orders.map((o) => (
                <Link
                  key={o.id}
                  to={o.report_ready ? `/reports/${o.id}` : '/dashboard/orders'}
                  className="order-mini-card"
                  style={{ textDecoration: 'none', color: 'inherit' }}
                >
                  <div className="order-mini-icon">📋</div>
                  <div className="order-mini-body">
                    <div className="order-mini-name">{o.tariff.name}</div>
                    <div className="order-mini-meta">
                      {dayjs(o.created_at).format('D MMM YYYY')} · {o.amount} ₽
                    </div>
                  </div>
                  {o.report_ready ? (
                    <span className="tag tag-green">{t('dashboard.homeTagReady')}</span>
                  ) : (
                    <span className="tag tag-blue">{o.status}</span>
                  )}
                </Link>
              ))
            )}
          </div>
        </div>

        <div className="upgrade-card">
          <div className="upgrade-title">{t('dashboard.homeSubscriptionBox')}</div>
          {sub ? (
            <>
              <div className="upgrade-features">
                <div className="upgrade-feat">✓ {sub.tariff_name}</div>
              </div>
              <Link to="/dashboard/subscription" className="btn btn-primary btn-sm">
                {t('dashboard.homeManageSub')}
              </Link>
            </>
          ) : (
            <p style={{ fontSize: 14, color: 'var(--text-2)', marginBottom: 12 }}>{t('dashboard.homeNoSub')}</p>
          )}
        </div>
      </div>
    </div>
  )
}
