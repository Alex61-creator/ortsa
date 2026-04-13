import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Button, Spin } from 'antd'
import { cancelMySubscription, fetchMySubscription, resumeMySubscription } from '@/api/subscriptions'
import dayjs from 'dayjs'

export function SubscriptionPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [showCancel, setShowCancel] = useState(false)
  const { data: sub, isLoading } = useQuery({ queryKey: ['subscription'], queryFn: fetchMySubscription })

  const cancelMut = useMutation({
    mutationFn: cancelMySubscription,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['subscription'] })
      setShowCancel(false)
    },
  })
  const resumeMut = useMutation({
    mutationFn: resumeMySubscription,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['subscription'] }),
  })

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin />
      </div>
    )
  }

  if (!sub || sub.status !== 'active') {
    return (
      <div className="card" style={{ padding: 32, textAlign: 'center' }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>✦</div>
        <div style={{ fontSize: 18, fontWeight: 500, marginBottom: 8 }}>{t('dashboard.subEmptyTitle')}</div>
        <div
          style={{
            fontSize: 14,
            color: 'var(--text-3)',
            marginBottom: 20,
            maxWidth: 360,
            marginLeft: 'auto',
            marginRight: 'auto',
          }}
        >
          {t('dashboard.subEmptyHint')}
        </div>
        <Link to="/order/tariff" className="btn btn-primary">
          {t('dashboard.subEmptyCta')}
        </Link>
      </div>
    )
  }

  const periodEnd = sub.current_period_end ? dayjs(sub.current_period_end) : null
  const periodEndFmt = periodEnd ? periodEnd.format('D MMMM YYYY') : '—'
  const connected = sub.current_period_start ? dayjs(sub.current_period_start).format('D MMM YYYY') : '—'
  const amount = sub.amount?.replace(/\.00$/, '') ?? sub.amount

  const features = [
    t('dashboard.subFeature1'),
    t('dashboard.subFeature2'),
    t('dashboard.subFeature3'),
    t('dashboard.subFeature4'),
    t('dashboard.subFeature5'),
    t('dashboard.subFeature6'),
  ]

  return (
    <div>
      <div className="sub-status-card">
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 16,
            marginBottom: 12,
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: 'var(--purple)',
                textTransform: 'uppercase',
                letterSpacing: '0.07em',
                marginBottom: 4,
              }}
            >
              {t('dashboard.subActiveBadge')}
            </div>
            <div className="sub-plan-name">{sub.tariff_name}</div>
          </div>
          <span className="tag tag-green" style={{ fontSize: 13, padding: '5px 12px' }}>
            {t('dashboard.subStatusTag')}
          </span>
        </div>
        <div className="sub-meta">
          <span>💳 {t('dashboard.subPriceMonth', { amount })}</span>
          {periodEnd && (
            <>
              <span>·</span>
              <span>
                {t('dashboard.subNextBilling', {
                  date: periodEndFmt,
                })}
              </span>
            </>
          )}
          <span>·</span>
          <span>{t('dashboard.subConnected', { date: connected })}</span>
        </div>
        {sub.status_message && (
          <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 16 }}>{sub.status_message}</p>
        )}
        <div className="sub-features">
          {features.map((feat) => (
            <div key={feat} className="sub-feat">
              <span style={{ color: 'var(--success)' }}>✓</span> {feat}
            </div>
          ))}
        </div>
        <div className="sub-actions">
          {sub.status === 'active' && !sub.cancel_at_period_end && (
            <button type="button" className="btn btn-danger btn-sm" onClick={() => setShowCancel(true)}>
              {t('dashboard.subCancel')}
            </button>
          )}
          {sub.status === 'active' && sub.cancel_at_period_end && (
            <Button type="primary" loading={resumeMut.isPending} onClick={() => void resumeMut.mutate()}>
              {t('dashboard.subResume')}
            </Button>
          )}
          {periodEnd && (
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
              {t('dashboard.subCancelHint', { date: periodEndFmt })}
            </span>
          )}
        </div>
      </div>

      {showCancel && sub.status === 'active' && !sub.cancel_at_period_end && (
        <div className="cancel-confirm show">
          <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--danger)', marginBottom: 8 }}>
            {t('dashboard.subCancelConfirmTitle')}
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 16, lineHeight: 1.6 }}>
            {t('dashboard.subCancelConfirmBody', { date: periodEndFmt })}
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              disabled={cancelMut.isPending}
              onClick={() => void cancelMut.mutate()}
            >
              {t('dashboard.subCancelYes')}
            </button>
            <button type="button" className="btn btn-default btn-sm" onClick={() => setShowCancel(false)}>
              {t('dashboard.subCancelKeep')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
