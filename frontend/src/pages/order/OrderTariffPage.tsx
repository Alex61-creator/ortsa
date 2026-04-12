import { Typography, Row, Col, Card, Button } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Steps } from 'antd'
import { listTariffs } from '@/api/tariffs'
import { useOrderWizardStore } from '@/stores/orderWizardStore'

const { Title } = Typography

export function OrderTariffPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setTariff = useOrderWizardStore((s) => s.setTariffCode)
  const { data: tariffs, isLoading } = useQuery({ queryKey: ['tariffs'], queryFn: listTariffs })

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: 24 }}>
      <Steps
        current={0}
        items={[
          { title: t('order.stepTariff') },
          { title: t('order.stepData') },
          { title: t('order.stepConfirm') },
        ]}
        style={{ marginBottom: 32 }}
      />
      <Title level={2}>{t('order.selectTariff')}</Title>
      <Row gutter={[24, 24]}>
        {(tariffs ?? []).map((tar) => (
          <Col xs={24} md={8} key={tar.code}>
            <Card loading={isLoading} title={tar.name}>
              <Title level={3}>{tar.price} ₽</Title>
              <Button
                type="primary"
                block
                onClick={() => {
                  setTariff(tar.code)
                  navigate('/order/data')
                }}
              >
                {t('common.continue')}
              </Button>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
