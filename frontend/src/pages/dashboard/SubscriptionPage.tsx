import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Button, Space, Spin, Typography } from 'antd'
import { cancelMySubscription, fetchMySubscription, resumeMySubscription } from '@/api/subscriptions'
import dayjs from 'dayjs'

const { Paragraph } = Typography

export function SubscriptionPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const { data: sub, isLoading } = useQuery({ queryKey: ['subscription'], queryFn: fetchMySubscription })

  const cancelMut = useMutation({
    mutationFn: cancelMySubscription,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['subscription'] }),
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

  if (!sub) {
    return (
      <div className="card">
        <div className="card-body">
          <Paragraph>{t('dashboard.subEmpty')}</Paragraph>
        </div>
      </div>
    )
  }

  return (
    <div className="sub-status-card">
      <div className="sub-plan-name">{sub.tariff_name}</div>
      <div className="sub-meta">
        <span>
          {t('dashboard.subAmount')}: {sub.amount} ₽
        </span>
        {sub.current_period_end && (
          <span>
            {t('dashboard.subUntil')}: {dayjs(sub.current_period_end).format('DD.MM.YYYY')}
          </span>
        )}
      </div>
      {sub.status_message && (
        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
          {sub.status_message}
        </Paragraph>
      )}
      <div className="sub-actions">
        <Space wrap>
          {sub.status === 'active' && !sub.cancel_at_period_end && (
            <Button loading={cancelMut.isPending} onClick={() => void cancelMut.mutate()}>
              {t('dashboard.subCancelEnd')}
            </Button>
          )}
          {sub.status === 'active' && sub.cancel_at_period_end && (
            <Button type="primary" loading={resumeMut.isPending} onClick={() => void resumeMut.mutate()}>
              {t('dashboard.subResume')}
            </Button>
          )}
        </Space>
      </div>
    </div>
  )
}
