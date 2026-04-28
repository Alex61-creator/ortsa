import { Button, Layout, Menu, Space } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useUiStore } from '@/stores/uiStore'
import { exportFirstTableAsCsv } from '@/utils/exportTableCsv'

const { Sider, Content } = Layout

const items = [
  { type: 'group', label: 'Аналитика', key: 'g-analytics', children: [
    { key: '/', label: <Link to="/">Дашборд</Link> },
    { key: '/funnel', label: <Link to="/funnel">Воронка</Link> },
    { key: '/growth', label: <Link to="/growth">Growth & Economics</Link> },
    { key: '/campaigns', label: <Link to="/campaigns">Кампании и UTM</Link> },
    { key: '/one-time-sales', label: <Link to="/one-time-sales">Разовые продажи</Link> },
    { key: '/report-options', label: <Link to="/report-options">Тумблеры отчёта</Link> },
    { key: '/promo-analytics', label: <Link to="/promo-analytics">Промо-аналитика</Link> },
    { key: '/subscriptions', label: <Link to="/subscriptions">Подписки</Link> },
  ] },
  { type: 'group', label: 'Пользователи', key: 'g-users', children: [
    { key: '/users', label: <Link to="/users">Пользователи</Link> },
    { key: '/payments', label: <Link to="/payments">Платежи</Link> },
    { key: '/orders', label: <Link to="/orders">Заказы</Link> },
  ] },
  { type: 'group', label: 'Инструменты', key: 'g-tools', children: [
    { key: '/tasks', label: <Link to="/tasks">Задачи Celery</Link> },
    { key: '/promos', label: <Link to="/promos">Промокоды</Link> },
    { key: '/prompts', label: <Link to="/prompts">Промпты LLM</Link> },
    { key: '/tariffs', label: <Link to="/tariffs">Тарифы</Link> },
    { key: '/flags', label: <Link to="/flags">Feature Flags</Link> },
  ] },
  { type: 'group', label: 'LLM', key: 'g-llm', children: [
    { key: '/llm-settings', label: <Link to="/llm-settings">LLM Настройки</Link> },
    { key: '/llm-analytics', label: <Link to="/llm-analytics">LLM Аналитика</Link> },
  ] },
  { type: 'group', label: 'Система', key: 'g-system', children: [
    { key: '/health', label: <Link to="/health">Мониторинг</Link> },
    { key: '/log', label: <Link to="/log">Лог действий</Link> },
    { key: '/settings', label: <Link to="/settings">Настройки</Link> },
  ] },
]

const TITLE_MAP: Record<string, string> = {
  '/': 'Дашборд',
  '/funnel': 'Воронка продаж',
  '/growth': 'Growth & Economics',
  '/campaigns': 'Кампании и UTM',
  '/one-time-sales': 'Разовые продажи',
  '/report-options': 'Тумблеры отчёта',
  '/promo-analytics': 'Промо-аналитика',
  '/subscriptions': 'Подписки',
  '/users': 'Пользователи',
  '/payments': 'Платежи',
  '/orders': 'Заказы',
  '/tasks': 'Задачи Celery',
  '/promos': 'Промокоды',
  '/tariffs': 'Тарифы',
  '/prompts': 'Промпты LLM',
  '/flags': 'Feature Flags',
  '/llm-settings': 'LLM Настройки',
  '/llm-analytics': 'LLM Аналитика',
  '/health': 'Мониторинг',
  '/log': 'Лог действий',
}

const ROUTES = Object.keys(TITLE_MAP)

export function AdminLayout() {
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const token = useAuthStore((s) => s.token)
  const theme = useUiStore((s) => s.theme)

  // Декодируем payload JWT (без верификации — только для отображения)
  const adminEmail = (() => {
    if (!token) return null
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return (payload.sub as string) ?? null
    } catch {
      return null
    }
  })()
  const toggleTheme = useUiStore((s) => s.toggleTheme)
  const adminInitial = (adminEmail ?? 'admin').slice(0, 1).toUpperCase()
  const selected = ['/', '/funnel', '/growth', '/campaigns', '/one-time-sales', '/report-options', '/promo-analytics', '/subscriptions', '/users', '/payments', '/orders', '/tasks', '/promos', '/prompts', '/tariffs', '/flags', '/llm-settings', '/llm-analytics', '/health', '/log', '/settings']
    .find((key) => (key === '/' ? location.pathname === '/' : location.pathname.startsWith(key)))
  document.documentElement.setAttribute('data-theme', theme)
  const titleMap: Record<string, string> = {
    '/': 'Дашборд',
    '/funnel': 'Воронка',
    '/growth': 'Growth & Economics',
    '/campaigns': 'Кампании и UTM',
    '/one-time-sales': 'Разовые продажи',
    '/report-options': 'Тумблеры отчёта',
    '/promo-analytics': 'Промо-аналитика',
    '/subscriptions': 'Подписки',
    '/users': 'Пользователи',
    '/payments': 'Платежи',
    '/orders': 'Заказы',
    '/tasks': 'Задачи Celery',
    '/promos': 'Промокоды',
    '/prompts': 'Промпты LLM',
    '/tariffs': 'Тарифы',
    '/flags': 'Feature Flags',
    '/llm-settings': 'LLM Настройки',
    '/llm-analytics': 'LLM Аналитика',
    '/health': 'Мониторинг',
    '/log': 'Лог действий',
    '/settings': 'Настройки',
  }
  const topbarTitle = selected ? titleMap[selected] : 'Админка'

  return (
    <Layout className="admin-shell" style={{ minHeight: '100vh' }}>
      <Sider
        breakpoint="lg"
        collapsedWidth={0}
        theme={theme === 'dark' ? 'dark' : 'light'}
        className="admin-sider"
        style={{ display: 'flex', flexDirection: 'column' }}
      >
        <div className="admin-brand">
          <div className="admin-brand-icon">
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="5.5" stroke="white" strokeWidth="1" fill="none" />
              <circle cx="7" cy="1.5" r="1.5" fill="white" />
            </svg>
          </div>
          Admin v2
          <span className="admin-badge">ADMIN</span>
        </div>

        <Menu
          mode="inline"
          selectedKeys={selected ? [selected] : []}
          items={items}
          style={{ flex: 1, overflowY: 'auto', border: 'none' }}
        />

        <div className="admin-sidebar-footer">
          <div className="admin-sidebar-ava">{adminInitial}</div>
          <div className="admin-sidebar-name">{adminEmail ?? 'admin'}</div>
          <button
            onClick={() => logout()}
            title="Выйти"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--ag-muted)',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
              <path
                d="M9.5 4.5L12 7l-2.5 2.5M12 7H5.5M5.5 2H2.5a1 1 0 00-1 1v8a1 1 0 001 1h3"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </Sider>

      <Layout>
        <div className="admin-header">
          <div className="admin-topbar-title">{topbarTitle}</div>
          <div className="admin-header-actions">
            <button
              onClick={() => toggleTheme()}
              style={{
                background: 'none',
                border: '1px solid var(--ag-border)',
                borderRadius: 'var(--ag-r)',
                cursor: 'pointer',
                padding: '5px 10px',
                fontSize: 16,
                color: 'var(--ag-text-2)',
                lineHeight: 1,
              }}
            >
              {theme === 'light' ? '☀' : '☾'}
            </button>
            <Space size={4}>
              <Button
                type="primary"
                size="small"
                onClick={() => exportFirstTableAsCsv(`admin-${topbarTitle}.csv`, false)}
              >
                ↓ CSV
              </Button>
              <Button
                size="small"
                title="UTF-8 BOM для Excel"
                onClick={() => exportFirstTableAsCsv(`admin-${topbarTitle}.csv`, true)}
              >
                BOM
              </Button>
            </Space>
          </div>
        </div>
        <Content className="admin-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
