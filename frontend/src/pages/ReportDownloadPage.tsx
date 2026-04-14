import { Typography, Button, Space, Result, Spin } from 'antd'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { downloadReportChart, downloadReportPdf } from '@/api/reports'
import { getOrder } from '@/api/orders'

const { Title } = Typography

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function ReportDownloadPage() {
  const { t } = useTranslation()
  const { orderId } = useParams<{ orderId: string }>()
  const id = Number(orderId)

  const { data: order, isLoading } = useQuery({
    queryKey: ['order', id],
    queryFn: () => getOrder(id),
    enabled: Number.isFinite(id),
  })

  const onPdf = async () => {
    const blob = await downloadReportPdf(id)
    saveBlob(blob, `natal_report_${id}.pdf`)
  }

  const onPng = async () => {
    const blob = await downloadReportChart(id)
    saveBlob(blob, `natal_chart_${id}.png`)
  }

  if (!Number.isFinite(id)) {
    return <Result status="error" title={t('reports.invalidLink')} />
  }

  if (isLoading) {
    return <Spin size="large" fullscreen />
  }

  if (order && !order.report_ready) {
    return (
      <div style={{ padding: 24, maxWidth: 560, margin: '0 auto' }}>
        <Result
          status="info"
          title={t('reports.preparingTitle')}
          extra={
            <Typography.Link href="/dashboard/orders">{t('reports.goToOrders')}</Typography.Link>
          }
        />
      </div>
    )
  }

  return (
    <div style={{ padding: 24, maxWidth: 560, margin: '0 auto' }}>
      <Title level={2}>{t('reports.title')}</Title>
      <Space direction="vertical" size="middle">
        <Button type="primary" size="large" onClick={() => void onPdf()}>
          {t('reports.pdf')}
        </Button>
        <Button size="large" onClick={() => void onPng()}>
          {t('reports.png')}
        </Button>
      </Space>
    </div>
  )
}
