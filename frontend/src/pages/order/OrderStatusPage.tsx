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
    return <Result status="error" title="Некорректный заказ" />
  }

  if (isLoading || !data) {
    return <Spin size="large" fullscreen tip={t('common.loading')} />
  }

  const done = data.status === 'completed' || data.status === 'paid'
  const failed = data.status === 'failed' || data.status === 'canceled'

  return (
    <div style={{ maxWidth: 560, margin: '0 auto', padding: 24 }}>
      <Typography.Title level={2}>{t('order.statusTitle')}</Typography.Title>
      <Paragraph>Статус: {data.status}</Paragraph>
      {done && (
        <>
          <Result
            status="success"
            title="Оплата прошла"
            subTitle={t('order.paidHint')}
            extra={
              <Space direction="vertical">
                {data.report_ready && (
                  <Link to={`/reports/${data.id}`}>
                    <Button type="primary">Открыть отчёт</Button>
                  </Link>
                )}
                {isTwa && (
                  <Paragraph type="secondary">
                    Когда отчёт будет готов, вы получите ссылку в боте или на почте.
                  </Paragraph>
                )}
                <Link to="/dashboard/orders">
                  <Button type="default">Мои заказы</Button>
                </Link>
              </Space>
            }
          />
        </>
      )}
      {data.status === 'pending' && (
        <Result
          status="info"
          title="Ожидаем оплату"
          subTitle="Завершите оплату в открывшемся окне ЮKassa."
        />
      )}
      {data.status === 'processing' && (
        <Result status="info" title="Генерация отчёта" subTitle="Обычно 5–15 минут." />
      )}
      {failed && <Result status="error" title="Проблема с заказом" subTitle={data.status} />}
    </div>
  )
}
