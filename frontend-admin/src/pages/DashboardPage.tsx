import { useEffect, useState } from 'react'
import { Button, Card, Space, Typography } from 'antd'
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
      {summary && (
        <div className="admin-kpi-grid">
          <div className="admin-metric-card">
            <div className="admin-metric-label">FAILED</div>
            <div className="admin-metric-value">{summary.order_metrics.failed_orders_total}</div>
            <div className="admin-metric-delta--down">Требуют ручной проверки</div>
          </div>
          <div className="admin-metric-card">
            <div className="admin-metric-label">MRR</div>
            <div className="admin-metric-value">{summary.business_metrics?.mrr ?? '—'}$</div>
            <div className="admin-metric-delta--up">+{summary.business_metrics?.new_mrr ?? 0}$ new</div>
          </div>
          <div className="admin-metric-card">
            <div className="admin-metric-label">Churn MRR</div>
            <div className="admin-metric-value">{summary.business_metrics?.churn_mrr ?? '—'}$</div>
            <div className="admin-metric-delta--down">Потери текущего периода</div>
          </div>
          <div className="admin-metric-card">
            <div className="admin-metric-label">LTV</div>
            <div className="admin-metric-value">{summary.business_metrics?.ltv ?? '—'}$</div>
            <div className="admin-metric-label">Среднее значение</div>
          </div>
          <div className="admin-metric-card">
            <div className="admin-metric-label">ROI LLM</div>
            <div className="admin-metric-value">{summary.llm_metrics?.roi_pct ?? '—'}%</div>
            <div className="admin-metric-label">Токены: {summary.llm_metrics?.tokens_total ?? '—'}</div>
          </div>
        </div>
      )}
      <div className="admin-two-col">
      <Card loading={loading} title="Операционная сводка">
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
      <Card title="LLM и экономика">
        <Paragraph>
          <strong>Затраты LLM:</strong> {summary?.llm_metrics?.llm_cost ?? '—'}$
          <br />
          <strong>Средняя стоимость отчета:</strong> {summary?.llm_metrics?.avg_report_cost ?? '—'}$
        </Paragraph>
        <Paragraph className="admin-muted">
          Обновлено: {summary ? new Date(summary.order_metrics.checked_at).toLocaleString('ru-RU') : '—'}
        </Paragraph>
      </Card>
      </div>
    </Space>
  )
}
