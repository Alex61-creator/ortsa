import { useMemo, useState } from 'react'
import { Typography, Button, Card, Steps, App, Switch, Flex, Space, Spin, Alert, Input } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery } from '@tanstack/react-query'
import { createOrder } from '@/api/orders'
import { listNatalData } from '@/api/natal'
import { listTariffs } from '@/api/tariffs'
import { getReportOrderOptions } from '@/api/reportOrderOptions'
import { useOrderWizardStore } from '@/stores/orderWizardStore'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'
import type { ReportOptionKey } from '@/constants/reportOptions'
import {
  buildReportOptionsPayload,
  computeToggleLinePreview,
  isReportUpsellTariff,
} from '@/constants/reportOptions'

const LS_DELIVERY_EMAIL = 'astrogen_delivery_email_override'

function getDeliveryEmail(): string | null {
  try {
    return localStorage.getItem(LS_DELIVERY_EMAIL) || null
  } catch {
    return null
  }
}

const { Title, Text } = Typography

function formatMoneyRub(n: number): string {
  return `${n.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`
}

export function OrderConfirmPage() {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const { isTwa } = useTwaEnvironment()
  const tariffCode = useOrderWizardStore((s) => s.tariffCode)
  const natalDataId = useOrderWizardStore((s) => s.natalDataId)
  const natalDataIds = useOrderWizardStore((s) => s.natalDataIds)
  const reportOptions = useOrderWizardStore((s) => s.reportOptions)
  const setReportOption = useOrderWizardStore((s) => s.setReportOption)
  const [promoCode, setPromoCode] = useState('')

  const isBundle = tariffCode === 'bundle'
  const upsellTariff = isReportUpsellTariff(tariffCode)

  const { data: tariffs } = useQuery({ queryKey: ['tariffs'], queryFn: listTariffs })
  const { data: natalList } = useQuery({ queryKey: ['natal-data'], queryFn: listNatalData })
  const reportOptsQuery = useQuery({
    queryKey: ['report-order-options'],
    queryFn: getReportOrderOptions,
    enabled: upsellTariff,
  })

  const tariff = tariffs?.find((x) => x.code === tariffCode)
  const natal = natalList?.find((x) => x.id === natalDataId)
  const bundleNatalProfiles = isBundle && natalDataIds.length > 0
    ? natalDataIds.map((id) => natalList?.find((x) => x.id === id)).filter(Boolean)
    : null

  const ro = reportOptsQuery.data
  const showReportOptionsBlock =
    upsellTariff && ro?.feature_enabled === true && (ro.options?.length ?? 0) > 0

  const priceByKey = useMemo(() => {
    const m: Record<string, number> = {}
    for (const o of ro?.options ?? []) {
      const p = parseFloat(o.price)
      m[o.key] = Number.isFinite(p) ? p : 0
    }
    return m
  }, [ro?.options])

  const baseAmount = tariff ? parseFloat(tariff.price) : 0
  const baseSafe = Number.isFinite(baseAmount) ? baseAmount : 0
  const multiPct = ro?.multi_discount_percent ?? 0
  const toggleLine = showReportOptionsBlock
    ? computeToggleLinePreview(reportOptions, priceByKey, multiPct)
    : 0
  const previewTotal = Math.round((baseSafe + toggleLine) * 100) / 100

  const pay = useMutation({
    mutationFn: async () => {
      if (!tariffCode || !natalDataId) throw new Error(t('order.incompleteDataError'))
      const deliveryEmail = getDeliveryEmail()
      const report_options =
        upsellTariff && showReportOptionsBlock ? buildReportOptionsPayload(reportOptions) : undefined
      return createOrder({
        tariff_code: tariffCode,
        natal_data_id: natalDataId,
        natal_data_ids: isBundle && natalDataIds.length > 0 ? natalDataIds : null,
        report_delivery_email: deliveryEmail,
        promo_code: promoCode.trim() || null,
        ...(report_options ? { report_options } : {}),
      })
    },
    onSuccess: (order) => {
      const url = order.confirmation_url
      const tg = window.Telegram?.WebApp
      if (!url) {
        navigate(`/order/status/${order.id}`, { replace: true })
        return
      }
      if (isTwa && tg?.openLink) {
        tg.openLink(url)
        navigate(`/order/status/${order.id}`, { replace: true })
      } else {
        window.location.assign(url)
      }
    },
    onError: () => {
      message.error('Не удалось инициировать платёж. Попробуйте ещё раз или свяжитесь с поддержкой.')
    },
  })

  if (!tariffCode || !natalDataId) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={4}>{t('order.confirmIncompleteSteps')}</Title>
        <Button onClick={() => navigate('/order/tariff')}>{t('common.startOver')}</Button>
      </div>
    )
  }

  return (
    <div className="order-step-shell">
      <Steps
        current={2}
        items={[
          { title: t('order.stepTariff') },
          { title: t('order.stepData') },
          { title: t('order.stepConfirm') },
        ]}
        style={{ marginBottom: 24 }}
      />
      <div style={{ fontSize: 12, color: 'var(--ag-text-secondary)', marginBottom: 14 }}>Шаг 3 из 3 - проверьте данные перед оплатой</div>
      <div className="order-confirm-grid">
        <div>
          {/* ── Натальные данные (bundle: несколько профилей) ── */}
          {isBundle && bundleNatalProfiles && bundleNatalProfiles.length > 0 ? (
            <Card style={{ marginBottom: 12 }}>
              <div className="order-review-head">
                <div className="order-review-title">Натальные профили ({bundleNatalProfiles.length})</div>
                <button type="button" style={{ border: 'none', background: 'none', color: 'var(--ag-primary)', cursor: 'pointer' }} onClick={() => navigate('/order/data')}>
                  Изменить
                </button>
              </div>
              {bundleNatalProfiles.map((nd, i) => nd && (
                <div key={nd.id} style={{ marginTop: i > 0 ? 12 : 4, paddingTop: i > 0 ? 12 : 0, borderTop: i > 0 ? '1px solid var(--ag-border)' : 'none' }}>
                  <div style={{ fontSize: 12, color: 'var(--ag-text-secondary)', marginBottom: 4 }}>Профиль {i + 1}</div>
                  <div className="order-review-rows">
                    <span>Имя</span>
                    <strong>{nd.full_name}</strong>
                    <span>Дата</span>
                    <strong>{new Date(nd.birth_date).toLocaleDateString('ru-RU')}</strong>
                    <span>Время</span>
                    <strong>{new Date(nd.birth_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</strong>
                    <span>Место</span>
                    <strong>{nd.birth_place}</strong>
                  </div>
                </div>
              ))}
            </Card>
          ) : (
            <Card style={{ marginBottom: 12 }}>
              <div className="order-review-head">
                <div className="order-review-title">Натальные данные</div>
                <button type="button" style={{ border: 'none', background: 'none', color: 'var(--ag-primary)', cursor: 'pointer' }} onClick={() => navigate('/order/data')}>
                  Изменить
                </button>
              </div>
              <div className="order-review-rows">
                <span>Имя</span>
                <strong>{natal?.full_name ?? '—'}</strong>
                <span>Дата</span>
                <strong>{natal?.birth_date ? new Date(natal.birth_date).toLocaleDateString('ru-RU') : '—'}</strong>
                <span>Время</span>
                <strong>{natal?.birth_time ? new Date(natal.birth_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '—'}</strong>
                <span>Место</span>
                <strong>{natal?.birth_place ?? '—'}</strong>
              </div>
            </Card>
          )}

          <Card>
            <div className="order-review-head">
              <div className="order-review-title">Выбранный тариф</div>
              <button type="button" style={{ border: 'none', background: 'none', color: 'var(--ag-primary)', cursor: 'pointer' }} onClick={() => navigate('/order/tariff')}>
                Изменить
              </button>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <div style={{ fontSize: 15, fontWeight: 600 }}>{tariff?.name ?? tariffCode}</div>
                <div style={{ fontSize: 12, color: 'var(--ag-text-secondary)' }}>
                  {tariff?.billing_type === 'subscription' ? 'Подписка' : 'Разовая покупка'}
                </div>
              </div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{tariff ? `${tariff.price} ₽` : '—'}</div>
            </div>
          </Card>

          {upsellTariff && reportOptsQuery.isLoading ? (
            <div style={{ marginTop: 12, display: 'flex', justifyContent: 'center', padding: 16 }}>
              <Spin />
            </div>
          ) : null}
          {upsellTariff && reportOptsQuery.isError ? (
            <Alert
              style={{ marginTop: 12 }}
              type="warning"
              showIcon
              message="Не удалось загрузить опции доп. разделов"
              description="Оплата возможна по базовому тарифу. Обновите страницу или попробуйте позже."
            />
          ) : null}

          {upsellTariff &&
          !reportOptsQuery.isLoading &&
          ro?.feature_enabled === true &&
          (ro.options?.length ?? 0) === 0 ? (
            <Alert
              style={{ marginTop: 12 }}
              type="warning"
              showIcon
              message="Дополнительные разделы сейчас недоступны"
              description="В админке не заданы цены опций или конфигурация неполная. Можно оплатить базовый тариф."
            />
          ) : null}

          {showReportOptionsBlock ? (
            <Card
              style={{
                marginTop: 12,
                borderRadius: 16,
              }}
              styles={{ body: { padding: '20px 22px' } }}
            >
              <Title level={5} style={{ marginTop: 0, marginBottom: 8 }}>
                Дополнительные разделы отчёта
              </Title>
              <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                Включите темы, которые хотите видеть отдельными блоками в PDF. При выборе двух и более разделов
                действует скидка {multiPct}% на их сумму. Промокоды не распространяются на эти разделы.
              </Text>
              <Space direction="vertical" size={14} style={{ width: '100%' }}>
                {ro!.options.map((opt) => {
                  const k = opt.key as ReportOptionKey
                  const checked = !!reportOptions[k]
                  const descId = `report-opt-desc-${opt.key}`
                  return (
                    <Flex
                      key={opt.key}
                      wrap="wrap"
                      gap={12}
                      align="flex-start"
                      justify="space-between"
                      style={{ width: '100%' }}
                    >
                      <div style={{ flex: '1 1 200px', minWidth: 0 }}>
                        <Title level={5} style={{ margin: 0, fontSize: 15 }}>
                          {opt.title}
                        </Title>
                        <Text type="secondary" id={descId} style={{ display: 'block', marginTop: 4 }}>
                          {opt.description}
                        </Text>
                        <Text type="secondary" style={{ display: 'block', marginTop: 6, fontSize: 12 }}>
                          +{opt.price} {opt.currency === 'RUB' ? '₽' : opt.currency}
                        </Text>
                      </div>
                      <Switch
                        checked={checked}
                        onChange={(v) => setReportOption(k, v)}
                        aria-label={`${opt.title}. ${opt.description}`}
                        aria-describedby={descId}
                      />
                    </Flex>
                  )
                })}
              </Space>
            </Card>
          ) : null}

          <div
            style={{
              marginTop: 12,
              padding: '10px 12px',
              border: '1px solid var(--ag-border)',
              borderRadius: 10,
              fontSize: 12,
              color: 'var(--ag-text-secondary)',
              background: 'color-mix(in srgb, var(--ag-bg-container) 94%, transparent)',
            }}
          >
            После нажатия «Оплатить» вы будете перенаправлены на защищенную страницу ЮKassa.
          </div>
        </div>

        <div>
          <div className="order-summary-box">
            <div className="order-summary-title">Итого к оплате</div>
            <div className="order-summary-amount">
              {tariff ? formatMoneyRub(showReportOptionsBlock ? previewTotal : baseSafe) : '—'}
            </div>
            {showReportOptionsBlock && toggleLine > 0 ? (
              <Text type="secondary" style={{ display: 'block', fontSize: 12, marginBottom: 8, lineHeight: 1.45 }}>
                База (тариф): {formatMoneyRub(baseSafe)} + доп. разделы: {formatMoneyRub(toggleLine)}
                {Object.values(reportOptions).filter(Boolean).length >= 2 && multiPct > 0
                  ? ` (включая скидку ${multiPct}% при 2+ разделах)`
                  : ''}
              </Text>
            ) : null}
            {isBundle && bundleNatalProfiles && (
              <div style={{ fontSize: 12, color: 'var(--ag-text-secondary)', marginBottom: 8 }}>
                {bundleNatalProfiles.length} отчёт{bundleNatalProfiles.length > 1 ? 'а' : ''} для разных профилей
              </div>
            )}
            <div className="order-summary-note">После оплаты откроется защищенная страница ЮKassa</div>
            <div style={{ marginBottom: 12 }}>
              <Input
                placeholder="Промокод (необязательно)"
                value={promoCode}
                onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                maxLength={50}
                allowClear
                aria-label="Промокод"
              />
              {pay.error ? (
                <div style={{ marginTop: 4, fontSize: 12, color: 'var(--ag-danger)' }}>
                  {(pay.error as any)?.response?.data?.detail ?? 'Ошибка оплаты'}
                </div>
              ) : null}
            </div>
            <Button type="primary" size="large" block loading={pay.isPending} onClick={() => pay.mutate()}>
              Оплатить через ЮKassa
            </Button>
            <div className="order-summary-meta">Visa, Mastercard, МИР, СБП, ЮMoney</div>
          </div>
          <div style={{ marginTop: 8 }}>
            <Button onClick={() => navigate('/order/tariff')}>← Изменить тариф</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
