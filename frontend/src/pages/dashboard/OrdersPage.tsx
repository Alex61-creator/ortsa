import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { Spin } from 'antd'
import { listOrders } from '@/api/orders'
import type { OrderListItem, OrderStatus } from '@/types/api'

type OrderFilter = 'all' | 'paid' | 'pending'

function orderRef(id: number, createdAt: string): string {
  const y = dayjs(createdAt).format('YYYY')
  return `#ORD-${y}-${String(id).padStart(4, '0')}`
}

function tariffSubline(o: OrderListItem, t: (k: string, o?: Record<string, string>) => string): string {
  const amt = Number(o.amount)
  if (amt === 0) return t('orders.tariffLineFree')
  if (o.tariff.billing_type === 'subscription') {
    return o.tariff.subscription_interval === 'year' ? t('orders.tariffLineSubYear') : t('orders.tariffLineSubMonth')
  }
  return t('orders.tariffLineOnce')
}

function statusTagClass(status: OrderStatus, reportReady: boolean): string {
  if (reportReady) return 'tag tag-green'
  if (status === 'completed' && !reportReady) return 'tag tag-gray'
  if (status === 'pending' || status === 'failed_to_init_payment') return 'tag tag-amber'
  if (status === 'paid' || status === 'processing') return 'tag tag-green'
  if (status === 'refunded') return 'tag tag-amber'
  return 'tag tag-gray'
}

function statusLabel(status: OrderStatus, reportReady: boolean, t: (k: string) => string): string {
  if (reportReady) return t('orders.statusPaid')
  if (status === 'completed') return t('orders.statusDone')
  if (status === 'pending' || status === 'failed_to_init_payment') return t('orders.statusPendingPay')
  if (status === 'paid' || status === 'processing') return t('orders.statusPaid')
  if (status === 'failed') return t('orders.statusFailed')
  if (status === 'refunded') return t('orders.statusRefunded')
  if (status === 'canceled') return t('orders.statusCanceled')
  return status
}

function matchesFilter(o: OrderListItem, f: OrderFilter): boolean {
  if (f === 'all') return true
  if (f === 'pending') return o.status === 'pending' || o.status === 'failed_to_init_payment'
  if (f === 'paid') return ['paid', 'processing', 'completed', 'refunded'].includes(o.status)
  return true
}

export function OrdersPage() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({ queryKey: ['orders'], queryFn: listOrders })
  const [filter, setFilter] = useState<OrderFilter>('all')

  const rows = useMemo(() => {
    const list = data ?? []
    return list.filter((o) => matchesFilter(o, filter))
  }, [data, filter])

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin />
      </div>
    )
  }

  return (
    <div>
      <div className="orders-filter">
        <button type="button" className={`filter-btn${filter === 'all' ? ' on' : ''}`} onClick={() => setFilter('all')}>
          {t('orders.filterAll')}
        </button>
        <button type="button" className={`filter-btn${filter === 'paid' ? ' on' : ''}`} onClick={() => setFilter('paid')}>
          {t('orders.filterPaid')}
        </button>
        <button
          type="button"
          className={`filter-btn${filter === 'pending' ? ' on' : ''}`}
          onClick={() => setFilter('pending')}
        >
          {t('orders.filterPending')}
        </button>
      </div>

      <div className="card">
        <div style={{ overflowX: 'auto' }}>
          <table className="orders-table">
            <thead>
              <tr>
                <th>{t('orders.colOrder')}</th>
                <th>{t('orders.colTariffAmount')}</th>
                <th>{t('orders.colDate')}</th>
                <th>{t('orders.colStatus')}</th>
                <th>{t('orders.colAction')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-3)', padding: 24 }}>
                    {t('orders.empty')}
                  </td>
                </tr>
              ) : (
                rows.map((o) => (
                  <tr key={o.id}>
                    <td>
                      <div className="order-name-cell">{o.tariff.name}</div>
                      <div className="order-id">{orderRef(o.id, o.created_at)}</div>
                    </td>
                    <td>
                      <strong>{o.amount} ₽</strong>
                      <br />
                      <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{tariffSubline(o, t)}</span>
                    </td>
                    <td>{dayjs(o.created_at).format('D MMM YYYY')}</td>
                    <td>
                      <span className={statusTagClass(o.status as OrderStatus, o.report_ready)}>
                        {statusLabel(o.status as OrderStatus, o.report_ready, t)}
                      </span>
                    </td>
                    <td>
                      <div className="order-actions">
                        {o.report_ready && (
                          <>
                            <Link to={`/reports/${o.id}`}>
                              <button type="button" className="btn btn-default btn-xs">
                                {o.tariff.code.toLowerCase().includes('bundle') ? '3 PDF' : t('orders.actionReport')}
                              </button>
                            </Link>
                            <Link to={`/reports/${o.id}`}>
                              <button type="button" className="btn btn-primary btn-xs">
                                PDF
                              </button>
                            </Link>
                            <Link to={`/reports/${o.id}`}>
                              <button type="button" className="btn btn-default btn-xs">
                                {t('orders.actionDetails')}
                              </button>
                            </Link>
                          </>
                        )}
                        {!o.report_ready && (o.status === 'paid' || o.status === 'processing') && (
                          <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{t('orders.actionWaitReport')}</span>
                        )}
                        {o.status === 'pending' && (
                          <Link to="/order/tariff">
                            <button type="button" className="btn btn-default btn-xs">
                              {t('orders.actionPay')}
                            </button>
                          </Link>
                        )}
                        {o.status === 'completed' && !o.report_ready && Number(o.amount) === 0 && (
                          <Link to="/order/tariff">
                            <button type="button" className="btn btn-default btn-xs">
                              {t('orders.actionUpsell')}
                            </button>
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="card-footer" style={{ fontSize: 12, color: 'var(--text-3)' }}>
          {t('orders.yookassaFooter')}{' '}
          <Link to="/dashboard/support" style={{ color: 'var(--primary)' }}>
            {t('orders.yookassaSupportLink')}
          </Link>
          .
        </div>
      </div>
    </div>
  )
}
