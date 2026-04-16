import { useEffect, useState } from 'react'
import { Alert, Card, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchPromoPerformance } from '@/api/metrics'
import type { PromoPerformanceRow } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const { Paragraph } = Typography

export function PromoAnalyticsPage() {
  const [methodology, setMethodology] = useState('')
  const [rows, setRows] = useState<PromoPerformanceRow[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchPromoPerformance()
      .then((d) => {
        setMethodology(d.methodology)
        setRows(d.rows)
      })
      .catch((e) => message.error(extractApiErrorMessage(e, 'Ошибка загрузки')))
      .finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<PromoPerformanceRow> = [
    { title: 'Промокод', dataIndex: 'promocode' },
    { title: 'Погашений', dataIndex: 'redemptions' },
    {
      title: 'Скидка всего, ₽',
      dataIndex: 'discount_total_rub',
      render: (v: number) => v.toLocaleString('ru-RU', { maximumFractionDigits: 2 }),
    },
    {
      title: 'Сумма заказов, ₽',
      dataIndex: 'order_revenue_rub',
      render: (v: number) => v.toLocaleString('ru-RU', { maximumFractionDigits: 2 }),
    },
  ]

  return (
    <>
      <Alert type="info" showIcon style={{ marginBottom: 16 }} message={methodology} />
      <Card title="Промокоды с погашениями">
        <Paragraph type="secondary" style={{ marginBottom: 12 }}>
          Только коды, по которым есть записи в <code>promocode_redemptions</code>.
        </Paragraph>
        <Table<PromoPerformanceRow>
          rowKey="promocode"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={{ pageSize: 20 }}
          size="small"
        />
      </Card>
    </>
  )
}
