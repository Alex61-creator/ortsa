import { useEffect, useState } from 'react'
import { Button, Card, Space, Tag, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { fetchDashboardSummary } from '@/api/dashboard'
import type { DashboardSummary } from '@/types/admin'

const { Paragraph, Text } = Typography

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    setErr(null)
    void fetchDashboardSummary()
      .then(setSummary)
      .catch(() => setErr('Не удалось загрузить сводку'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card loading={loading} title="Дашборд">
        {err && <Text type="danger">{err}</Text>}
        {summary && (
          <>
            <Paragraph>
              <strong>Failed</strong> — заказы с ошибкой генерации; разберите вручную или перезапустите
              отчёт из раздела «Заказы».
            </Paragraph>
            <Paragraph>
              <strong>Processing &gt; 2 ч</strong> — долго висят в генерации; проверьте Celery и логи.
            </Paragraph>
            <Paragraph>
              Failed: <strong>{summary.order_metrics.failed_orders_total}</strong>
              <br />
              Processing &gt; 2ч:{' '}
              <strong>{summary.order_metrics.processing_stuck_over_2h}</strong>
              <br />
              <Text type="secondary">
                Обновлено: {new Date(summary.order_metrics.checked_at).toLocaleString('ru-RU')}
              </Text>
            </Paragraph>
            <Link to="/orders">
              <Button type="primary">Перейти к заказам</Button>
            </Link>
          </>
        )}
      </Card>
      <Card title="Аналитика (позже)">
        <Tag color="orange">Заглушка</Tag>
        <Paragraph style={{ marginTop: 8 }}>
          Воронка, UTM, промокоды — см. <Text code>docs/ADMIN_PANEL_FUTURE.md</Text>
        </Paragraph>
      </Card>
    </Space>
  )
}
