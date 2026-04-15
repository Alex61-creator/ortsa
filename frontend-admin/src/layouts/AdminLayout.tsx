import { Button, Layout, Menu, Space, Typography } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useUiStore } from '@/stores/uiStore'
import { exportFirstTableAsCsv } from '@/utils/exportTableCsv'

const { Header, Sider, Content } = Layout

const items = [
  { type: 'group', label: 'Аналитика', key: 'g-analytics', children: [
    { key: '/', label: <Link to="/">Дашборд</Link> },
    { key: '/funnel', label: <Link to="/funnel">Воронка</Link> },
  ] },
  { type: 'group', label: 'Пользователи', key: 'g-users', children: [
    { key: '/users', label: <Link to="/users">Пользователи</Link> },
    { key: '/payments', label: <Link to="/payments">Платежи</Link> },
    { key: '/orders', label: <Link to="/orders">Заказы</Link> },
  ] },
  { type: 'group', label: 'Инструменты', key: 'g-tools', children: [
    { key: '/tasks', label: <Link to="/tasks">Задачи Celery</Link> },
    { key: '/promos', label: <Link to="/promos">Промокоды</Link> },
    { key: '/tariffs', label: <Link to="/tariffs">Тарифы</Link> },
    { key: '/flags', label: <Link to="/flags">Feature Flags</Link> },
  ] },
  { type: 'group', label: 'Система', key: 'g-system', children: [
    { key: '/health', label: <Link to="/health">Мониторинг</Link> },
    { key: '/log', label: <Link to="/log">Лог действий</Link> },
    { key: '/settings', label: <Link to="/settings">Настройки</Link> },
  ] },
]

export function AdminLayout() {
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const theme = useUiStore((s) => s.theme)
  const toggleTheme = useUiStore((s) => s.toggleTheme)
  const selected = ['/', '/funnel', '/users', '/payments', '/orders', '/tasks', '/promos', '/tariffs', '/flags', '/health', '/log', '/settings']
    .find((key) => (key === '/' ? location.pathname === '/' : location.pathname.startsWith(key)))
  document.documentElement.setAttribute('data-theme', theme)
  const titleMap: Record<string, string> = {
    '/': 'Дашборд',
    '/funnel': 'Воронка',
    '/users': 'Пользователи',
    '/payments': 'Платежи',
    '/orders': 'Заказы',
    '/tasks': 'Задачи Celery',
    '/promos': 'Промокоды',
    '/tariffs': 'Тарифы',
    '/flags': 'Feature Flags',
    '/health': 'Мониторинг',
    '/log': 'Лог действий',
    '/settings': 'Настройки',
  }
  const topbarTitle = selected ? titleMap[selected] : 'Админка'

  return (
    <Layout className="admin-shell">
      <Sider breakpoint="lg" collapsedWidth={0} theme={theme} className="admin-sider">
        <div className="admin-brand">
          AstroGen Admin
          <span className="admin-badge">ADMIN</span>
        </div>
        <Menu mode="inline" selectedKeys={selected ? [selected] : []} items={items} />
      </Sider>
      <Layout>
        <Header className="admin-header">
          <div className="admin-topbar-title">{topbarTitle}</div>
          <div className="admin-header-actions">
            <Button onClick={() => toggleTheme()}>{theme === 'light' ? 'Темная' : 'Светлая'}</Button>
            <Button type="primary" onClick={() => exportFirstTableAsCsv(`admin-${topbarTitle}.csv`)}>
              Экспорт CSV
            </Button>
            <Space size={4}>
              <span className="admin-muted">ADMIN</span>
              <Typography.Link onClick={() => logout()}>Выйти</Typography.Link>
            </Space>
          </div>
        </Header>
        <Content className="admin-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
