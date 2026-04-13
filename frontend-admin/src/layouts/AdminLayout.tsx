import { Layout, Menu, Typography } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

const { Header, Sider, Content } = Layout

const items = [
  { key: '/', label: <Link to="/">Дашборд</Link> },
  { key: '/orders', label: <Link to="/orders">Заказы</Link> },
  { key: '/users', label: <Link to="/users">Пользователи</Link> },
  { key: '/tariffs', label: <Link to="/tariffs">Тарифы</Link> },
]

export function AdminLayout() {
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const selected = items.find((i) =>
    i.key === '/' ? location.pathname === '/' : location.pathname.startsWith(i.key)
  )?.key

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={0} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: 16, fontWeight: 600 }}>AstroGen Admin</div>
        <Menu mode="inline" selectedKeys={selected ? [selected] : []} items={items} />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Typography.Link onClick={() => logout()}>Выйти</Typography.Link>
        </Header>
        <Content style={{ padding: 24, background: '#f5f5f5' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
