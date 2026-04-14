import { useEffect, useState } from 'react'
import { Card, Progress, Select, Space, Typography } from 'antd'
import { fetchFunnelSummary } from '@/api/funnel'
import type { FunnelSummary } from '@/types/admin'

export function FunnelPage() {
  const [summary, setSummary] = useState<FunnelSummary | null>(null)
  const [period, setPeriod] = useState('current_month')

  useEffect(() => {
    void fetchFunnelSummary(period).then(setSummary).catch(() => setSummary(null))
  }, [period])

  return (
    <>
      <div className="admin-page-title">Воронка</div>
      <Card
        title={summary ? `Период: ${summary.period}` : 'Воронка'}
        extra={(
          <Select
            value={period}
            onChange={setPeriod}
            style={{ width: 180 }}
            options={[
              { value: 'today', label: 'Сегодня' },
              { value: 'current_week', label: 'Эта неделя' },
              { value: 'current_month', label: 'Этот месяц' },
            ]}
          />
        )}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {(summary?.steps ?? []).map((item) => (
            <div key={item.key}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Typography.Text>{item.title}</Typography.Text>
                <Typography.Text type="secondary">{item.count}</Typography.Text>
              </Space>
              <Progress percent={Number(item.conversion_pct.toFixed(1))} showInfo={false} />
            </div>
          ))}
          {!!summary?.drop_offs?.length && (
            <>
              <Typography.Title level={5}>Отвалы по этапам</Typography.Title>
              {summary.drop_offs.map((drop) => (
                <div key={`${drop.from_key}-${drop.to_key}`} className="admin-drawer-block">
                  <Typography.Text>
                    {drop.from_key} → {drop.to_key}: потеряно {drop.lost}
                  </Typography.Text>
                </div>
              ))}
            </>
          )}
          {!!summary?.recommendations?.length && (
            <>
              <Typography.Title level={5}>Рекомендации</Typography.Title>
              {summary.recommendations.map((item) => (
                <div key={item} className="admin-drawer-block">
                  <Typography.Text>{item}</Typography.Text>
                </div>
              ))}
            </>
          )}
        </Space>
      </Card>
    </>
  )
}
