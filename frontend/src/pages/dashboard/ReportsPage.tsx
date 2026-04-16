import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { listOrders } from '@/api/orders'
import { listNatalData } from '@/api/natal'
import { listAddons, purchaseAddon } from '@/api/addons'
import type { OrderListItem } from '@/types/api'
import { isSubscriptionTariffCode } from '@/constants/tariffs'

function reportIconClass(order: OrderListItem): string {
  if (Number(order.amount) === 0) return 'report-icon archived'
  if (order.tariff.code.toLowerCase().includes('bundle')) return 'report-icon purple'
  return 'report-icon'
}

function reportTag(order: OrderListItem): { cls: string; label: string } {
  if (Number(order.amount) === 0) return { cls: 'tag tag-gray', label: 'Бесплатный' }
  if (order.tariff.code.toLowerCase().includes('bundle')) return { cls: 'tag tag-amber', label: 'Набор «3»' }
  if (isSubscriptionTariffCode(order.tariff.code)) return { cls: 'tag tag-purple', label: 'Astro Pro' }
  return { cls: 'tag tag-purple', label: order.tariff.code.toUpperCase() }
}

export function ReportsPage() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({ queryKey: ['orders'], queryFn: listOrders })
  const { data: natalData } = useQuery({ queryKey: ['natal-data'], queryFn: listNatalData })
  const { data: addons } = useQuery({ queryKey: ['addons'], queryFn: listAddons })
  const purchaseMut = useMutation({
    mutationFn: (code: string) => purchaseAddon(code),
    onSuccess: (payload) => {
      if (payload.payment_url) window.location.href = payload.payment_url
    },
  })
  const ready = (data ?? [])
    .filter((o) => o.report_ready)
    .sort((a, b) => dayjs(b.created_at).valueOf() - dayjs(a.created_at).valueOf())
  const natalById = new Map((natalData ?? []).map((n) => [n.id, n]))

  if (isLoading) {
    return <p style={{ color: 'var(--text-3)' }}>{t('common.loading')}</p>
  }

  return (
    <div>
      {(addons ?? []).some((a) => a.eligible) && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="card-body">
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Доступные add-on</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {(addons ?? [])
                .filter((a) => a.eligible)
                .map((addon) => (
                  <button
                    key={addon.addon_code}
                    className="btn btn-default btn-sm"
                    disabled={purchaseMut.isPending}
                    onClick={() => purchaseMut.mutate(addon.addon_code)}
                  >
                    {addon.title} · {Number(addon.price).toLocaleString('ru-RU')} {addon.currency}
                  </button>
                ))}
            </div>
          </div>
        </div>
      )}
      {ready.length === 0 ? (
        <div className="card">
          <div className="card-body">
            <p style={{ color: 'var(--text-3)' }}>{t('dashboard.reportsEmpty')}</p>
          </div>
        </div>
      ) : (
        ready.map((o) => {
          const tag = reportTag(o)
          const isFree = Number(o.amount) === 0
          const natal = o.natal_data_id ? natalById.get(o.natal_data_id) : null
          const personLine = natal
            ? `${natal.full_name} · ${dayjs(natal.birth_date).format('DD.MM.YYYY')} · ${natal.birth_place} · ${dayjs(natal.birth_time).format('HH:mm')}`
            : dayjs(o.created_at).format('D MMM YYYY')
          return (
            <article className="report-card" key={o.id}>
              <div className="report-head">
                <div className={reportIconClass(o)}>{o.tariff.code.toLowerCase().includes('bundle') ? '☽' : '☉'}</div>
                <div className="report-info">
                  <div className="report-name">
                    {natal?.full_name ? `${natal.full_name} · ${o.tariff.name}` : o.tariff.name}
                  </div>
                  <div className="report-meta">
                    <span>{personLine}</span>
                    <span>·</span>
                    <span className={tag.cls} style={{ fontSize: 11 }}>
                      {tag.label}
                    </span>
                  </div>
                </div>
                <div className="report-actions">
                  {isFree ? <span className="tag tag-gray">1 страница</span> : <span className="tag tag-green">Активен</span>}
                  {isFree ? (
                    <Link to={`/reports/${o.id}`} className="btn btn-default btn-sm">
                      Открыть
                    </Link>
                  ) : (
                    <Link to={`/reports/${o.id}`} className="btn btn-primary btn-sm">
                      Скачать PDF
                    </Link>
                  )}
                </div>
              </div>
              <div className="report-detail">
                <span>Создан: {dayjs(o.created_at).format('D MMM YYYY, HH:mm')}</span>
                <span>·</span>
                <span>Тариф: {o.tariff.name}</span>
                <span>·</span>
                {isFree ? (
                  <>
                    <span>Базовая версия</span>
                    <span>·</span>
                    <Link to="/order/tariff" className="btn-link">
                      Докупить полный →
                    </Link>
                  </>
                ) : (
                  <>
                    <span>Хранится: по сроку тарифа</span>
                    <span>·</span>
                    <Link to={`/dashboard/orders`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>
                      #ORD-{dayjs(o.created_at).format('YYYY')}-{String(o.id).padStart(4, '0')}
                    </Link>
                  </>
                )}
              </div>
            </article>
          )
        })
      )}
    </div>
  )
}
