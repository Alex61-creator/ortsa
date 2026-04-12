import { Typography, Table, Button, Tag } from 'antd'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { listOrders } from '@/api/orders'
import type { OrderListItem, OrderStatus } from '@/types/api'

const { Title } = Typography

const statusColor: Record<OrderStatus, string> = {
  pending: 'default',
  paid: 'processing',
  processing: 'processing',
  completed: 'success',
  failed: 'error',
  refunded: 'warning',
  canceled: 'default',
}

export function OrdersPage() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({ queryKey: ['orders'], queryFn: listOrders })

  return (
    <div>
      <Title level={2}>{t('orders.title')}</Title>
      <Table<OrderListItem>
        loading={isLoading}
        rowKey="id"
        dataSource={data ?? []}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 80 },
          {
            title: t('orders.status'),
            dataIndex: 'status',
            render: (s: OrderStatus) => <Tag color={statusColor[s] ?? 'default'}>{s}</Tag>,
          },
          { title: t('orders.tariff'), render: (_, r) => r.tariff.name },
          { title: t('orders.amount'), dataIndex: 'amount' },
          {
            title: 'Создан',
            render: (_, r) => dayjs(r.created_at).format('DD.MM.YYYY HH:mm'),
          },
          {
            title: t('orders.report'),
            render: (_, r) =>
              r.report_ready ? (
                <Link to={`/reports/${r.id}`}>
                  <Button type="link">{t('orders.openReport')}</Button>
                </Link>
              ) : (
                '—'
              ),
          },
        ]}
      />
    </div>
  )
}
