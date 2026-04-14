import { Typography, Result, Button, Space, Spin } from 'antd'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { getOrder } from '@/api/orders'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'

const { Paragraph } = Typography

export function OrderStatusPage() {
  const { t } = useTranslation()
  const { orderId } = useParams<{ orderId: string }>()
  const id = Number(orderId)
  const { isTwa } = useTwaEnvironment()

  const { data, isLoading } = useQuery({
    queryKey: ['order', id],
    queryFn: () => getOrder(id),
    enabled: Number.isFinite(id),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      if (s === 'pending' || s === 'paid' || s === 'processing') return 4000
      return false
    },
  })

  if (!Number.isFinite(id)) {
    return <Result status="error" title={t('order.invalidOrder')} />
  }

  if (isLoading || !data) {
    return <Spin size="large" fullscreen tip={t('common.loading')} />
  }

  const done = data.status === 'completed' || data.status === 'paid'
  const failed = data.status === 'failed' || data.status === 'canceled'

  return (
    <div style={{ maxWidth: 560, margin: '0 auto', padding: 24 }}>
      <Typography.Title level={2}>{t('order.statusTitle')}</Typography.Title>
      <Paragraph>{t('order.statusLabel', { status: data.status })}</Paragraph>
      {done && (
        <>
          <Result
            status="success"
            title={t('order.paidTitle')}
            subTitle={t('order.paidHint')}
            extra={
              <Space direction="vertical">
                {data.report_ready && (
                  <Link to={`/reports/${data.id}`}>
                    <Button type="primary">{t('order.openReport')}</Button>
                  </Link>
                )}
                {isTwa && (
                  <Paragraph type="secondary">
                    {t('order.reportReadyHint')}
                  </Paragraph>
                )}
                <Link to="/dashboard/orders">
                  <Button type="default">{t('order.myOrders')}</Button>
                </Link>
              </Space>
            }
          />
        </>
      )}
      {data.status === 'pending' && (
        <Result
          status="info"
          title={t('order.pendingTitle')}
          subTitle={t('order.pendingHint')}
        />
      )}
      {data.status === 'processing' && (
        <Result status="info" title={t('order.processingTitle')} subTitle={t('order.processingHint')} />
      )}
      {failed && <Result status="error" title={t('order.problemTitle')} subTitle={data.status} />}
    </div>
  )
}
