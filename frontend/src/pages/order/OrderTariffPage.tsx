import { Alert, Button, Card, Col, Row, Steps, Tag, Typography } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMemo, useState } from 'react'
import { listTariffs } from '@/api/tariffs'
import { useOrderWizardStore } from '@/stores/orderWizardStore'
import type { TariffPublic } from '@/types/api'
import '@/styles/order-pricing.css'

const { Title } = Typography
type PricingMode = 'onetime' | 'subscription'

interface PlanFeature {
  label: string
  enabled: boolean
}

interface OneTimePlanModel {
  code: string
  title: string
  description: string
  period: string
  cta: string
  features: PlanFeature[]
  ribbon?: string
  ribbonTone?: 'blue' | 'green'
  isPopular?: boolean
  oldPrice?: number | null
  badge?: string
}

function toNumber(value: string): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function formatRub(value: number): string {
  return new Intl.NumberFormat('ru-RU').format(Math.round(value))
}

export function OrderTariffPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }
  const setTariff = useOrderWizardStore((s) => s.setTariffCode)
  const { data: tariffs, isLoading } = useQuery({ queryKey: ['tariffs'], queryFn: listTariffs })
  const redirectNote = location.state?.from
  const [mode, setMode] = useState<PricingMode>('onetime')
  const [isYearly, setIsYearly] = useState(true)
  const oneTimePlans = useMemo<OneTimePlanModel[]>(
    () => [
      {
        code: 'free',
        title: t('order.planFreeTitle'),
        description: t('order.planFreeDesc'),
        period: t('order.planFreePeriod'),
        cta: t('order.planFreeCta'),
        features: [
          { label: t('order.planFreeFeat1'), enabled: true },
          { label: t('order.planFreeFeat2'), enabled: true },
          { label: t('order.planFreeFeat3'), enabled: true },
          { label: t('order.planFreeFeat4'), enabled: true },
          { label: t('order.planFreeFeat5'), enabled: false },
          { label: t('order.planFreeFeat6'), enabled: false },
        ],
      },
      {
        code: 'report',
        title: t('order.planReportTitle'),
        description: t('order.planReportDesc'),
        period: t('order.planReportPeriod'),
        cta: t('order.planReportCta'),
        ribbon: t('order.planReportRibbon'),
        ribbonTone: 'blue',
        isPopular: true,
        features: [
          { label: t('order.planReportFeat1'), enabled: true },
          { label: t('order.planReportFeat2'), enabled: true },
          { label: t('order.planReportFeat3'), enabled: true },
          { label: t('order.planReportFeat4'), enabled: true },
          { label: t('order.planReportFeat5'), enabled: true },
          { label: t('order.planReportFeat6'), enabled: false },
        ],
      },
      {
        code: 'bundle',
        title: t('order.planBundleTitle'),
        description: t('order.planBundleDesc'),
        period: t('order.planBundlePeriod'),
        cta: t('order.planBundleCta'),
        ribbon: t('order.planBundleRibbon'),
        ribbonTone: 'green',
        badge: '-33%',
        features: [
          { label: t('order.planBundleFeat1'), enabled: true },
          { label: t('order.planBundleFeat2'), enabled: true },
          { label: t('order.planBundleFeat3'), enabled: true },
          { label: t('order.planBundleFeat4'), enabled: true },
          { label: t('order.planBundleFeat5'), enabled: false },
        ],
      },
    ],
    [t],
  )

  const tariffsByCode = useMemo(() => {
    const map = new Map<string, TariffPublic>()
    for (const tariff of tariffs ?? []) {
      map.set(tariff.code, tariff)
    }
    return map
  }, [tariffs])

  const proTariff = tariffsByCode.get('pro')
  const proMonthly = toNumber(proTariff?.price ?? '0')
  const proYearlyMonthly = Math.max(0, Math.round(proMonthly * 0.66))
  const proYearlyTotal = proYearlyMonthly * 12

  const startOrderFor = (tariffCode: string) => {
    setTariff(tariffCode)
    navigate('/order/data')
  }

  const resolvePlanPrice = (plan: OneTimePlanModel): { current: number; old: number | null } => {
    const apiTariff = tariffsByCode.get(plan.code)
    const current = toNumber(apiTariff?.price ?? '0')
    if (plan.code === 'bundle') {
      const old = Math.round(current * (2370 / 1590))
      return { current, old }
    }
    return { current, old: plan.oldPrice ?? null }
  }

  return (
    <div className="pricing-page">
      {redirectNote && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 24, maxWidth: 1120, marginInline: 'auto' }}
          message={t('order.loginToContinue', { place: redirectNote })}
        />
      )}
      <div className="pricing-shell">
        <Steps
          current={0}
          items={[
            { title: t('order.stepTariff') },
            { title: t('order.stepData') },
            { title: t('order.stepConfirm') },
          ]}
          style={{ marginBottom: 28 }}
        />
        <div className="pricing-header">
          <Title level={2} style={{ marginBottom: 8 }}>
            {t('order.selectTariff')}
          </Title>
          <p className="pricing-subtitle">{t('order.selectTariffSubtitle')}</p>
        </div>

        <div className="pricing-mode-switch">
          <button
            type="button"
            className={`pricing-mode-btn${mode === 'onetime' ? ' active' : ''}`}
            onClick={() => setMode('onetime')}
          >
            {t('order.modeOnetime')}
          </button>
          <button
            type="button"
            className={`pricing-mode-btn${mode === 'subscription' ? ' active' : ''}`}
            onClick={() => setMode('subscription')}
          >
            {t('order.modeSubscription')}
            <span className="pricing-mode-badge">{t('order.modeBetter')}</span>
          </button>
        </div>

        {mode === 'onetime' ? (
          <>
            <Alert
              type="info"
              showIcon
              className="pricing-hint"
              message={t('order.hintSubCheaper')}
            />
            <Row gutter={[20, 20]}>
              {oneTimePlans.map((plan) => {
                const price = resolvePlanPrice(plan)
                return (
                  <Col xs={24} md={8} key={plan.code}>
                    <Card
                      className={`pricing-card${plan.isPopular ? ' pricing-card-popular' : ''}`}
                      loading={isLoading}
                      bordered={false}
                    >
                      {plan.ribbon && (
                        <div className={`pricing-ribbon ${plan.ribbonTone === 'green' ? 'green' : 'blue'}`}>{plan.ribbon}</div>
                      )}
                      <div className="pricing-card-title">{plan.title}</div>
                      <div className="pricing-card-desc">{plan.description}</div>
                      <div className="pricing-price-wrap">
                        <div className="pricing-price-line">
                          <span className="pricing-price-main">{formatRub(price.current)}</span>
                          <span className="pricing-price-currency">₽</span>
                        </div>
                        <div className="pricing-price-period">{plan.period}</div>
                        {price.old ? (
                          <div className="pricing-price-meta">
                            <span className="pricing-price-old">{formatRub(price.old)} ₽</span>
                            {plan.badge ? <Tag color="green">{plan.badge}</Tag> : null}
                          </div>
                        ) : null}
                      </div>
                      <ul className="pricing-features">
                        {plan.features.map((feature, idx) => (
                          <li key={`${plan.code}-${idx}`} className={feature.enabled ? 'ok' : 'off'}>
                            {feature.enabled ? '✓' : '✕'} {feature.label}
                          </li>
                        ))}
                      </ul>
                      <Button
                        type={plan.isPopular ? 'primary' : 'default'}
                        block
                        size="large"
                        onClick={() => startOrderFor(plan.code)}
                      >
                        {plan.cta}
                      </Button>
                    </Card>
                  </Col>
                )
              })}
            </Row>
            <div className="pricing-switch-link">
              {t('order.switchToProPrompt')}
              <Button
                type="link"
                onClick={() => setMode('subscription')}
                style={{ paddingInline: 6 }}
              >
                {t('order.switchToProCta')}
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="billing-toggle">
              <span className={!isYearly ? 'active' : ''}>{t('order.billingMonthly')}</span>
              <Button type={isYearly ? 'primary' : 'default'} size="small" onClick={() => setIsYearly((v) => !v)}>
                {isYearly ? t('order.billingPlanYear') : t('order.billingMonthly')}
              </Button>
              <span className={isYearly ? 'active' : ''}>{t('order.billingYearly')}</span>
              {isYearly ? <Tag color="purple">{t('order.discount34')}</Tag> : null}
            </div>
            <Card className="pro-card" bordered={false}>
              <div className="pro-grid">
                <div>
                  <Tag color="purple">Astro Pro</Tag>
                  <Title level={3} style={{ marginTop: 10 }}>
                    {t('order.proTitle')}
                  </Title>
                  <p className="pro-copy">{t('order.proCopy')}</p>
                  <ul className="pro-features">
                    <li>{t('order.proFeatTransits')}</li>
                    <li>{t('order.proFeatSynastry')}</li>
                    <li>{t('order.proFeatProgressions')}</li>
                    <li>{t('order.proFeatProfiles')}</li>
                    <li>{t('order.proFeatReport')}</li>
                  </ul>
                </div>
                <div className="pro-price-box">
                  {isYearly ? <div className="pro-price-old">{formatRub(proMonthly)} ₽/мес</div> : null}
                  <div className="pro-price-main">
                    {formatRub(isYearly ? proYearlyMonthly : proMonthly)}
                    <span> ₽</span>
                  </div>
                  <div className="pro-price-subtitle">{t('order.perMonth')}</div>
                  <div className="pro-price-note">
                    {isYearly
                      ? t('order.yearlySinglePayment', { amount: formatRub(proYearlyTotal) })
                      : t('order.yearlyMonthlyPayment', { amount: formatRub(proMonthly * 12) })}
                  </div>
                  <Button type="primary" size="large" block onClick={() => startOrderFor('pro')}>
                    {isYearly ? t('order.payYearlyCta', { amount: formatRub(proYearlyTotal) }) : t('order.trialCta')}
                  </Button>
                </div>
              </div>
            </Card>
            <div className="pricing-switch-link">
              {t('order.switchToOneTimePrompt')}
              <Button type="link" onClick={() => setMode('onetime')} style={{ paddingInline: 6 }}>
                {t('order.switchToOneTimeCta')}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
