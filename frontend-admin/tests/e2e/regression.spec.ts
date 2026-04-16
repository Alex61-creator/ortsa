import { expect, test } from '@playwright/test'

const json = (body: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify(body),
})

test.beforeEach(async ({ page }) => {
  await page.route('**/admin/dashboard/summary', (route) =>
    route.fulfill(json({ order_metrics: { failed_orders_total: 1, processing_stuck_over_2h: 2, checked_at: new Date().toISOString() }, analytics_stub: false, future_docs: '' }))
  )
  await page.route('**/admin/orders/**', (route) => {
    const url = route.request().url()
    if (url.includes('/retry-report') || url.includes('/refund')) return route.fulfill(json({ queued: true, status: 'processing', order_id: 1 }))
    return route.fulfill(
      json([
        {
          id: 1,
          user_id: 1,
          status: 'paid',
          amount: '100.00',
          natal_data_id: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          tariff: { code: 'report', name: 'Отчёт', billing_type: 'one_time', subscription_interval: null },
          report_ready: true,
        },
      ])
    )
  })
  await page.route('**/admin/users/**', (route) =>
    route.fulfill(
      json([
        {
          id: 1,
          email: 'user@example.com',
          oauth_provider: 'google',
          is_admin: false,
          created_at: new Date().toISOString(),
          consent_given_at: null,
        },
      ])
    )
  )
  await page.route('**/admin/tariffs/**', (route) =>
    route.fulfill(
      json([
        {
          id: 1,
          code: 'report',
          name: 'Отчёт',
          price: '100.00',
          price_usd: '1.00',
          compare_price_usd: null,
          annual_total_usd: null,
          features: {},
          retention_days: 30,
          priority: 1,
          billing_type: 'one_time',
          subscription_interval: null,
          llm_tier: 'natal_full',
        },
      ])
    )
  )
  await page.route('**/admin/tariffs/history/list', (route) =>
    route.fulfill(json([{ id: '1', tariff_id: 1, actor: 'admin', payload: { price: '100.00' }, created_at: new Date().toISOString() }]))
  )
  await page.route('**/admin/payments/**', (route) =>
    route.fulfill(
      json([
        {
          order_id: 1,
          user_id: 1,
          user_email: 'user@example.com',
          status: 'paid',
          amount: '100.00',
          tariff_name: 'Отчёт',
          created_at: new Date().toISOString(),
        },
      ])
    )
  )
  await page.route('**/admin/funnel/**', (route) =>
    route.fulfill(json({ period: 'current_month', steps: [{ key: 'landing', title: 'Лендинг', count: 100, conversion_pct: 100 }] }))
  )
  await page.route('**/admin/tasks/**', (route) =>
    route.fulfill(json([{ id: '1', queue: 'reports', name: 'generate_report_task', status: 'running', created_at: new Date().toISOString(), updated_at: new Date().toISOString() }]))
  )
  await page.route('**/admin/promos/**', (route) =>
    route.fulfill(json([{ id: 'p1', code: 'SPRING', discount_percent: 20, max_uses: 10, used_count: 1, active_until: null, is_active: true }]))
  )
  await page.route('**/admin/prompts/**', (route) =>
    route.fulfill(json([{ tariff_code: 'free', locale: 'ru', system_prompt: 'Prompt', is_custom: false, updated_at: null, updated_by: null }]))
  )
  await page.route('**/admin/flags/**', (route) =>
    route.fulfill(json([{ key: 'admin_funnel_enabled', description: 'flag', enabled: true }]))
  )
  await page.route('**/admin/metrics/overview**', (route) =>
    route.fulfill(json({
      period_start: new Date().toISOString(),
      period_end: new Date().toISOString(),
      cards: [{ key: 'cr1', label: 'CR1', value: 0.2, previous_value: 0.1, delta_pct: 100, unit: 'ratio' }],
      alerts: [],
    }))
  )
  await page.route('**/admin/metrics/economics**', (route) =>
    route.fulfill(json({
      period_start: new Date().toISOString(),
      period_end: new Date().toISOString(),
      blended_cac: 1000,
      ltv_cac: 2.4,
      contribution_margin: 0.4,
      aov: 1200,
      attach_rate: 0.2,
      channel_cac: [{ channel: 'tg_ads', spend: 1000, first_paid_users: 2, cac: 500 }],
      action_hints: ['hint'],
    }))
  )
  await page.route('**/admin/metrics/cohorts**', (route) =>
    route.fulfill(json({
      period_start: new Date().toISOString(),
      period_end: new Date().toISOString(),
      rows: [{ cohort: '2026-04', size: 10, m1: 50, m3: 30, m6: 10 }],
    }))
  )
  await page.route('**/admin/metrics/funnel**', (route) =>
    route.fulfill(json({ period: 'current_month', steps: [] }))
  )
  await page.route('**/admin/metrics/spend**', (route) =>
    route.fulfill(json([]))
  )
  await page.route('**/admin/health/**', (route) =>
    route.fulfill(json([{ name: 'API', status: 'ok', value: 'online' }]))
  )
  await page.route('**/admin/logs/**', (route) =>
    route.fulfill(json([{ id: '1', actor_email: 'admin@example.com', action: 'flag_patch', entity: 'admin_funnel_enabled', created_at: new Date().toISOString() }]))
  )
  await page.route('**/admin/support/**', (route) => route.fulfill(json([])))
})

test('navigates through all admin sections', async ({ page }) => {
  await page.goto('/login')
  await page.evaluate(() => {
    localStorage.setItem('astrogen_admin_auth_token', JSON.stringify({ state: { token: 'test-token' }, version: 0 }))
  })
  await page.goto('/')
  await expect(page.locator('.admin-topbar-title')).toContainText('Дашборд')

  const routes = ['/funnel', '/growth', '/users', '/payments', '/orders', '/tasks', '/promos', '/prompts', '/tariffs', '/flags', '/health', '/log']
  for (const route of routes) {
    await page.goto(route)
    await expect(page.locator('body')).toContainText(/.+/)
  }
})
