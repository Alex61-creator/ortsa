import { Button, Layout, Menu } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useUiStore } from '@/stores/uiStore'
import { exportFirstTableAsCsv } from '@/utils/exportTableCsv'

const { Sider, Content } = Layout

const items = [
  {
    type: 'group' as const,
    label: 'Аналитика',
    key: 'g-analytics',
    children: [
      { key: '/', label: <Link to="/">Дашборд</Link> },
      { key: '/funnel', label: <Link to="/funnel">Воронка</Link> },
    ],
  },
  {
    type: 'group' as const,
    label: 'Пользователи',
    key: 'g-users',
    children: [
      { key: '/users', label: <Link to="/users">Пользователи</Link> },
      { key: '/payments', label: <Link to="/payments">Платежи</Link> },
      { key: '/orders', label: <Link to="/orders">Заказы</Link> },
    ],
  },
  {
    type: 'group' as const,
    label: 'Инструменты',
    key: 'g-tools',
    children: [
      { key: '/tasks', label: <Link to="/tasks">Задачи Celery</Link> },
      { key: '/promos', label: <Link to="/promos">Промокоды</Link> },
      { key: '/tariffs', label: <Link to="/tariffs">Тарифы</Link> },
      { key: '/flags', label: <Link to="/flags">Feature Flags</Link> },
    ],
  },
  {
    type: 'group' as const,
    label: 'Система',
    key: 'g-system',
    children: [
      { key: '/health', label: <Link to="/health">Мониторинг</Link> },
      { key: '/log', label: <Link to="/log">Лог действий</Link> },
    ],
  },
]

const TITLE_MAP: Record<string, string> = {
  '/': 'Дашборд',
  '/funnel': 'Воронка продаж',
  '/users': 'Пользователи',
  '/payments': 'Платежи',
  '/orders': 'Заказы',
  '/tasks': 'Задачи Celery',
  '/promos': 'Промокоды',
  '/tariffs': 'Тарифы',
  '/flags': 'Feature Flags',
  '/health': 'Мониторинг',
  '/log': 'Лог действий',
}

const ROUTES = Object.keys(TITLE_MAP)

export function AdminLayout() {
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const adminEmail = useAuthStore((s) => s.token)
  const theme = useUiStore((s) => s.theme)
  const toggleTheme = useUiStore((s) => s.toggleTheme)

  document.documentElement.setAttribute('data-theme', theme)

  const selected = ROUTES.find((key) =>
    key === '/' ? location.pathname === '/' : location.pathname.startsWith(key)
  )
  const topbarTitle = selected ? TITLE_MAP[selected] : 'Администрирование'
  const adminInitial = adminEmail ? adminEmail.slice(0, 1).toUpperCase() : 'A'

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
          <div className="admin-sidebar-name">admin@astrogen.ru</div>
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
            <Button
              type="primary"
              size="small"
              onClick={() => exportFirstTableAsCsv(`admin-${topbarTitle}.csv`)}
            >
              ↓ CSV
            </Button>
          </div>
        </div>
        <Content className="admin-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
