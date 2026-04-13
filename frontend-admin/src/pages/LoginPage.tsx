import { Button, Card, Space, Typography } from 'antd'

const { Title, Text } = Typography

function googleAdminUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? ''
  return `${base}/api/v1/auth/google/authorize-admin`
}

export function LoginPage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: '#f0f2f5',
      }}
    >
      <Card style={{ maxWidth: 400, width: '100%' }}>
        <Title level={4} style={{ textAlign: 'center' }}>
          Astrogen Admin
        </Title>
        <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: 16 }}>
          Вход только для аккаунтов с правами администратора (is_admin).
        </Text>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Button type="primary" block href={googleAdminUrl()}>
            Войти через Google
          </Button>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Telegram Mini App: откройте бота в Telegram и используйте тот же API{' '}
            <code>POST /api/v1/auth/twa</code> с этим доменом в настройках бота; после входа вставьте
            токен вручную или реализуйте виджет на этой странице.
          </Text>
        </Space>
      </Card>
    </div>
  )
}
