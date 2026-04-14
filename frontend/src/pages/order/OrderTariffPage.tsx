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
const REQUIRED_ONE_TIME_CODES = ['free', 'report', 'bundle'] as const

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
  const { data: tariffs, isLoading, isError } = useQuery({ queryKey: ['tariffs'], queryFn: listTariffs })
  const redirectNote = location.state?.from
  const [mode, setMode] = useState<PricingMode>('onetime')
  const [selectedOneTime, setSelectedOneTime] = useState('report')

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

  const missingCodes = useMemo(
    () => REQUIRED_ONE_TIME_CODES.filter((code) => !tariffsByCode.has(code)),
    [tariffsByCode],
  )

  const subMonthly = tariffsByCode.get('sub_monthly')
  const subAnnual = tariffsByCode.get('sub_annual')
  const tariffLoadFailed = isError || (!isLoading && missingCodes.length > 0)

  const startOrderFor = (tariffCode: string) => {
    setTariff(tariffCode)
    navigate('/order/data')
  }

  const resolvePlanPrice = (plan: OneTimePlanModel): { current: number | null; old: number | null } => {
    const apiTariff = tariffsByCode.get(plan.code)
    if (!apiTariff) return { current: null, old: null }
    const current = toNumber(apiTariff.price)
    if (plan.code === 'bundle') {
      const old = Math.round(current * (2370 / 1590))
      return { current, old }
    }
    return { current, old: plan.oldPrice ?? null }
  }

  const selectedOneTimePlan = oneTimePlans.find((plan) => plan.code === selectedOneTime) ?? oneTimePlans[0]
  const selectedOneTimeUnavailable = resolvePlanPrice(selectedOneTimePlan).current === null

  const monthlyPrice = subMonthly ? toNumber(subMonthly.price) : null
  const annualPrice = subAnnual ? toNumber(subAnnual.price) : null
  // Месячный эквивалент годовой подписки (для сравнения)
  const annualMonthly = annualPrice !== null ? Math.round(annualPrice / 12) : null
  const annualDiscount = monthlyPrice && annualMonthly
    ? Math.round((1 - annualMonthly / monthlyPrice) * 100)
    : null

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

        {tariffLoadFailed && (
          <Alert
            type="error"
            showIcon
            className="pricing-api-alert"
            message={t('order.tariffLoadError')}
            description={t('order.tariffLoadErrorHint')}
          />
        )}

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
                      className={`pricing-card${plan.isPopular ? ' pricing-card-popular' : ''}${selectedOneTime === plan.code ? ' pricing-card-selected' : ''}`}
                      loading={isLoading}
                      bordered={false}
                      onClick={() => {
                        if (price.current !== null) setSelectedOneTime(plan.code)
                      }}
                    >
                      {plan.ribbon && (
                        <div className={`pricing-ribbon ${plan.ribbonTone === 'green' ? 'green' : 'blue'}`}>{plan.ribbon}</div>
                      )}
                      <div className="pricing-card-title">{plan.title}</div>
                      <div className="pricing-card-desc">{plan.description}</div>
                      <div className="pricing-price-wrap">
                        {price.current === null ? (
                          <div className="pricing-price-unavailable">{t('order.tariffUnavailable')}</div>
                        ) : (
                          <>
                            <div className="pricing-price-line">
                              <span className="pricing-price-main">{formatRub(price.current)}</span>
                              <span className="pricing-price-currency">₽</span>
                            </div>
                            <div className="pricing-price-period">{plan.period}</div>
                          </>
                        )}
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
                        disabled={price.current === null}
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
              <Button type="link" onClick={() => setMode('subscription')} style={{ paddingInline: 6 }}>
                {t('order.switchToProCta')}
              </Button>
            </div>
            <div className="pricing-step-nav">
              <button type="button" className="pricing-nav-btn" onClick={() => navigate('/dashboard')}>
                ← Назад
              </button>
              <button
                type="button"
                className="pricing-nav-btn pricing-nav-btn-primary"
                disabled={selectedOneTimeUnavailable}
                onClick={() => startOrderFor(selectedOneTime)}
              >
                Далее → Проверить заказ
              </button>
            </div>
          </>
        ) : (
          <>
            <Row gutter={[20, 20]}>
              {/* ── Помесячная подписка ── */}
              <Col xs={24} md={12}>
                <Card className="pro-card" bordered={false}>
                  <div style={{ marginBottom: 8 }}>
                    <Tag color="blue">Astro Pro</Tag>
                    <span style={{ marginLeft: 8, fontSize: 13, color: 'var(--ag-text-2)' }}>Помесячно</span>
                  </div>
                  <Title level={4} style={{ margin: '8px 0' }}>{t('order.proTitle')}</Title>
                  <p style={{ color: 'var(--ag-text-2)', fontSize: 13 }}>{t('order.proCopy')}</p>
                  <ul className="pro-features">
                    <li>{t('order.proFeatTransits')}</li>
                    <li>{t('order.proFeatSynastry')}</li>
                    <li>{t('order.proFeatProgressions')}</li>
                    <li>До 5 натальных профилей</li>
                    <li>{t('order.proFeatReport')}</li>
                  </ul>
                  <div style={{ marginTop: 16 }}>
                    {monthlyPrice === null ? (
                      <div className="pricing-price-unavailable">{t('order.tariffUnavailable')}</div>
                    ) : (
                      <>
                        <div className="pro-price-main">
                          {formatRub(monthlyPrice)}<span> ₽</span>
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--ag-text-2)', marginBottom: 12 }}>
                          в месяц · списание ежемесячно
                        </div>
                      </>
                    )}
                    <Button
                      type="default"
                      size="large"
                      block
                      disabled={monthlyPrice === null}
                      onClick={() => startOrderFor('sub_monthly')}
                    >
                      {monthlyPrice === null ? t('order.tariffUnavailableCta') : t('order.trialCta')}
                    </Button>
                  </div>
                </Card>
              </Col>

              {/* ── Годовая подписка ── */}
              <Col xs={24} md={12}>
                <Card className="pro-card" bordered={false} style={{ border: '2px solid var(--ag-primary)' }}>
                  <div style={{ marginBottom: 8 }}>
                    <Tag color="purple">Astro Pro</Tag>
                    <span style={{ marginLeft: 8, fontSize: 13, color: 'var(--ag-text-2)' }}>Годовая</span>
                    {annualDiscount && annualDiscount > 0 ? (
                      <Tag color="green" style={{ marginLeft: 8 }}>−{annualDiscount}%</Tag>
                    ) : null}
                  </div>
                  <Title level={4} style={{ margin: '8px 0' }}>{t('order.proTitle')}</Title>
                  <p style={{ color: 'var(--ag-text-2)', fontSize: 13 }}>{t('order.proCopy')}</p>
                  <ul className="pro-features">
                    <li>{t('order.proFeatTransits')}</li>
                    <li>{t('order.proFeatSynastry')}</li>
                    <li>{t('order.proFeatProgressions')}</li>
                    <li>До 5 натальных профилей</li>
                    <li>{t('order.proFeatReport')}</li>
                  </ul>
                  <div style={{ marginTop: 16 }}>
                    {annualPrice === null ? (
                      <div className="pricing-price-unavailable">{t('order.tariffUnavailable')}</div>
                    ) : (
                      <>
                        {monthlyPrice && annualMonthly ? (
                          <div style={{ fontSize: 13, color: 'var(--ag-muted)', textDecoration: 'line-through', marginBottom: 2 }}>
                            {formatRub(monthlyPrice)} ₽/мес
                          </div>
                        ) : null}
                        <div className="pro-price-main">
                          {annualMonthly !== null ? formatRub(annualMonthly) : '—'}<span> ₽</span>
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--ag-text-2)', marginBottom: 4 }}>в месяц</div>
                        <div style={{ fontSize: 12, color: 'var(--ag-muted)', marginBottom: 12 }}>
                          Единый платёж {annualPrice !== null ? formatRub(annualPrice) : '—'} ₽/год
                        </div>
                      </>
                    )}
                    <Button
                      type="primary"
                      size="large"
                      block
                      disabled={annualPrice === null}
                      onClick={() => startOrderFor('sub_annual')}
                    >
                      {annualPrice === null
                        ? t('order.tariffUnavailableCta')
                        : annualPrice !== null
                          ? t('order.payYearlyCta', { amount: formatRub(annualPrice) })
                          : '—'}
                    </Button>
                  </div>
                </Card>
              </Col>
            </Row>

            <div className="pricing-switch-link">
              {t('order.switchToOneTimePrompt')}
              <Button type="link" onClick={() => setMode('onetime')} style={{ paddingInline: 6 }}>
                {t('order.switchToOneTimeCta')}
              </Button>
            </div>
            <div className="pricing-step-nav">
              <button type="button" className="pricing-nav-btn" onClick={() => navigate('/dashboard')}>
                ← Назад
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
