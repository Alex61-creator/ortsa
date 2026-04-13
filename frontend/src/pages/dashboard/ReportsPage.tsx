import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Button } from 'antd'
import { listOrders } from '@/api/orders'

export function ReportsPage() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({ queryKey: ['orders'], queryFn: listOrders })
  const ready = (data ?? []).filter((o) => o.report_ready)

  if (isLoading) {
    return <p style={{ color: 'var(--text-3)' }}>{t('common.loading')}</p>
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{t('dashboard.navReports')}</div>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        {ready.length === 0 ? (
          <p style={{ padding: 24, color: 'var(--text-3)' }}>{t('dashboard.reportsEmpty')}</p>
        ) : (
          <table className="orders-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>{t('orders.tariff')}</th>
                <th>{t('orders.amount')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {ready.map((o) => (
                <tr key={o.id}>
                  <td className="order-id">#{o.id}</td>
                  <td className="order-name-cell">{o.tariff.name}</td>
                  <td>{o.amount}</td>
                  <td className="order-actions">
                    <Link to={`/reports/${o.id}`}>
                      <Button type="link">{t('orders.openReport')}</Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
