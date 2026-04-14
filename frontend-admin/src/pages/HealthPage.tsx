import { useEffect, useState } from 'react'
import { Button, Card, Col, Row, Space, Tag, Typography } from 'antd'
import { fetchHealthWidgets } from '@/api/health'
import type { HealthWidget } from '@/types/admin'

export function HealthPage() {
  const [rows, setRows] = useState<HealthWidget[]>([])
  useEffect(() => {
    void fetchHealthWidgets().then(setRows).catch(() => setRows([]))
  }, [])

  return (
    <>
      <div className="admin-page-title">Мониторинг</div>
      <div className="admin-metric-grid" style={{ marginBottom: 12 }}>
        <div className="admin-metric-card"><div className="admin-metric-label">OK</div><div className="admin-metric-value">{rows.filter((r) => r.status === 'ok').length}</div></div>
        <div className="admin-metric-card"><div className="admin-metric-label">ERROR</div><div className="admin-metric-value">{rows.filter((r) => r.status !== 'ok').length}</div></div>
        <div className="admin-metric-card"><div className="admin-metric-label">Latency</div><div className="admin-metric-value">~120ms</div></div>
        <div className="admin-metric-card"><div className="admin-metric-label">Incidents</div><div className="admin-metric-value">1</div></div>
      </div>
      <Row gutter={[12, 12]}>
        {rows.map((row) => (
          <Col span={8} key={row.name}>
            <Card title={row.name}>
              <Typography.Title level={4}>{row.value}</Typography.Title>
              <Tag color={row.status === 'ok' ? 'green' : 'red'}>{row.status}</Tag>
            </Card>
          </Col>
        ))}
      </Row>
      <Card title="Последние ошибки (Sentry)" style={{ marginTop: 12 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div className="admin-drawer-block">
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Typography.Text>payments.retry.timeout</Typography.Text>
              <Tag color="red">high</Tag>
            </Space>
            <Button size="small">Решено</Button>
          </div>
        </Space>
      </Card>
    </>
  )
}
