import { Typography, Button, Card, Descriptions, Steps, Space } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery } from '@tanstack/react-query'
import { createOrder } from '@/api/orders'
import { listNatalData } from '@/api/natal'
import { listTariffs } from '@/api/tariffs'
import { useOrderWizardStore } from '@/stores/orderWizardStore'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'

const { Title } = Typography

export function OrderConfirmPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { isTwa } = useTwaEnvironment()
  const tariffCode = useOrderWizardStore((s) => s.tariffCode)
  const natalDataId = useOrderWizardStore((s) => s.natalDataId)

  const { data: tariffs } = useQuery({ queryKey: ['tariffs'], queryFn: listTariffs })
  const { data: natalList } = useQuery({ queryKey: ['natal-data'], queryFn: listNatalData })

  const tariff = tariffs?.find((x) => x.code === tariffCode)
  const natal = natalList?.find((x) => x.id === natalDataId)

  const pay = useMutation({
    mutationFn: async () => {
      if (!tariffCode || !natalDataId) throw new Error('Неполные данные')
      return createOrder({ tariff_code: tariffCode, natal_data_id: natalDataId })
    },
    onSuccess: (order) => {
      const url = order.confirmation_url
      const tg = window.Telegram?.WebApp
      if (!url) return
      if (isTwa && tg?.openLink) {
        tg.openLink(url)
        navigate(`/order/status/${order.id}`, { replace: true })
      } else {
        window.location.assign(url)
      }
    },
  })

  if (!tariffCode || !natalDataId) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={4}>Не хватает шагов оформления</Title>
        <Button onClick={() => navigate('/order/tariff')}>Начать сначала</Button>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: 24 }}>
      <Steps
        current={2}
        items={[
          { title: t('order.stepTariff') },
          { title: t('order.stepData') },
          { title: t('order.stepConfirm') },
        ]}
        style={{ marginBottom: 32 }}
      />
      <Title level={2}>Подтверждение</Title>
      <Card>
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="Тариф">{tariff?.name ?? tariffCode}</Descriptions.Item>
          <Descriptions.Item label="Цена">{tariff ? `${tariff.price} ₽` : '—'}</Descriptions.Item>
          <Descriptions.Item label="Имя">{natal?.full_name}</Descriptions.Item>
          <Descriptions.Item label="Место">{natal?.birth_place}</Descriptions.Item>
        </Descriptions>
        <Space style={{ marginTop: 24 }}>
          <Button onClick={() => navigate('/order/data')}>{t('common.back')}</Button>
          <Button type="primary" loading={pay.isPending} onClick={() => pay.mutate()}>
            {t('order.pay')}
          </Button>
        </Space>
      </Card>
    </div>
  )
}
