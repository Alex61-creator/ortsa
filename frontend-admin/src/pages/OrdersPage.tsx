import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  Card,
  Drawer,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Spin,
  Table,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchOrder, fetchOrders, postRefund, postRetryReport } from '@/api/orders'
import { downloadOrderChart, downloadOrderPdf } from '@/api/reports'
import type { AdminOrderRow } from '@/types/admin'
import { isAxiosError } from 'axios'

const { Text } = Typography

function statusTag(status: string) {
  switch (status) {
    case 'paid':                  return <span className="ag-tag ag-tag-green">paid</span>
    case 'completed':             return <span className="ag-tag ag-tag-teal">completed</span>
    case 'processing':            return <span className="ag-tag ag-tag-blue">processing</span>
    case 'pending':               return <span className="ag-tag ag-tag-amber">pending</span>
    case 'failed':                return <span className="ag-tag ag-tag-red">failed</span>
    case 'refunded':              return <span className="ag-tag ag-tag-purple">refunded</span>
    case 'canceled':              return <span className="ag-tag ag-tag-gray">canceled</span>
    case 'failed_to_init_payment':return <span className="ag-tag ag-tag-red">init failed</span>
    default:                      return <span className="ag-tag ag-tag-gray">{status}</span>
  }
}

function tariffTag(code: string) {
  if (code?.includes('pro'))   return <span className="ag-tag ag-tag-purple">{code}</span>
  if (code?.includes('sub'))   return <span className="ag-tag ag-tag-blue">{code}</span>
  return <span className="ag-tag ag-tag-gray">{code}</span>
}

const STATUS_OPTIONS = [
  { value: '', label: 'Все статусы' },
  { value: 'pending', label: 'pending' },
  { value: 'failed_to_init_payment', label: 'failed_to_init_payment' },
  { value: 'paid', label: 'paid' },
  { value: 'processing', label: 'processing' },
  { value: 'completed', label: 'completed' },
  { value: 'failed', label: 'failed' },
  { value: 'refunded', label: 'refunded' },
  { value: 'canceled', label: 'canceled' },
]

export function OrdersPage() {
  const [page, setPage]           = useState(1)
  const [pageSize, setPageSize]   = useState(20)
  const [status, setStatus]       = useState<string | undefined>(undefined)
  const [userId, setUserId]       = useState<number | null>(null)
  const [q, setQ]                 = useState('')
  const qRef                      = useRef(q)
  qRef.current                    = q
  const [rows, setRows]           = useState<AdminOrderRow[]>([])
  const [loading, setLoading]     = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selected, setSelected]   = useState<AdminOrderRow | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchOrders({
        page,
        page_size: pageSize,
        status: status || undefined,
        user_id: userId ?? undefined,
        q: qRef.current.trim() || undefined,
      })
      setRows(data)
    } catch {
      message.error('Не удалось загрузить заказы')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, status, userId])

  useEffect(() => { void load() }, [load])

  const openDrawer = async (row: AdminOrderRow) => {
    setSelected(row)
    setDrawerOpen(true)
    setDrawerLoading(true)
    try {
      const fresh = await fetchOrder(row.id)
      setSelected(fresh)
    } catch {
      message.error('Не удалось обновить заказ')
    } finally {
      setDrawerLoading(false)
    }
  }

  const handleRetry = async () => {
    if (!selected) return
    try {
      await postRetryReport(selected.id)
      message.success('Задача генерации поставлена в очередь')
      const fresh = await fetchOrder(selected.id)
      setSelected(fresh)
      void load()
    } catch (e) {
      if (isAxiosError(e) && e.response?.status === 429) {
        const d = e.response?.data as { detail?: string }
        message.error(d?.detail ?? 'Лимит перезапусков')
      } else {
        message.error('Не удалось перезапустить отчёт')
      }
    }
  }

  const handleRefund = () => {
    if (!selected) return
    const amountRef = { current: '' }
    Modal.confirm({
      title: `Возврат по заказу #${selected.id}`,
      content: (
        <div>
          <p style={{ color: 'var(--ag-text-2)', fontSize: 13 }}>
            Оставьте пустым для полного возврата. Максимум: {selected.amount} ₽
          </p>
          <Input
            placeholder="Сумма (опционально)"
            onChange={(e) => { amountRef.current = e.target.value }}
          />
        </div>
      ),
      okText: 'Инициировать возврат',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const amt = amountRef.current.trim()
          await postRefund(selected.id, amt || undefined)
          message.success('Возврат инициирован')
          const fresh = await fetchOrder(selected.id)
          setSelected(fresh)
          void load()
        } catch (e) {
          if (isAxiosError(e)) {
            const d = e.response?.data as { detail?: string }
            message.error(d?.detail ?? 'Ошибка возврата')
          } else {
            message.error('Ошибка возврата')
          }
        }
      },
    })
  }

  const total =
    rows.length < pageSize
      ? (page - 1) * pageSize + rows.length
      : page * pageSize + 1

  const columns: ColumnsType<AdminOrderRow> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 70,
      render: (v: number) => (
        <span style={{ fontFamily: 'monospace', color: 'var(--ag-primary)' }}>#{v}</span>
      ),
    },
    {
      title: 'User ID',
      dataIndex: 'user_id',
      width: 80,
      render: (v: number) => (
        <span style={{ fontSize: 12, color: 'var(--ag-muted)' }}>{v}</span>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      render: (s: string) => statusTag(s),
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      render: (v: string) => {
        const n = parseFloat(v)
        return <span style={{ fontWeight: 500 }}>{isNaN(n) ? v : `${n.toLocaleString('ru-RU')} ₽`}</span>
      },
    },
    {
      title: 'Тариф',
      render: (_, r) => tariffTag(r.tariff.code),
    },
    {
      title: 'Отчёт',
      dataIndex: 'report_ready',
      render: (v: boolean) =>
        v
          ? <span className="ag-tag ag-tag-green">готов</span>
          : <span className="ag-tag ag-tag-gray">нет</span>,
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      render: (t: string) =>
        new Date(t).toLocaleString('ru-RU', {
          day: '2-digit', month: '2-digit', year: '2-digit',
          hour: '2-digit', minute: '2-digit',
        }),
    },
  ]

  return (
    <>
      {/* ── Toolbar ── */}
      <Card style={{ marginBottom: 12 }}>
        <div className="admin-toolbar">
          <Select
            style={{ width: 220 }}
            value={status ?? ''}
            options={STATUS_OPTIONS}
            size="small"
            onChange={(v) => { setStatus(v || undefined); setPage(1) }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>user_id</Text>
            <InputNumber
              min={1}
              size="small"
              value={userId ?? undefined}
              onChange={(v) => { setUserId(typeof v === 'number' ? v : null); setPage(1) }}
              style={{ width: 90 }}
            />
          </div>
          <Input
            placeholder="ID заказа"
            size="small"
            style={{ width: 120 }}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onPressEnter={() => { setPage(1); void load() }}
          />
          <Button type="primary" size="small" onClick={() => void load()}>
            Обновить
          </Button>
        </div>
      </Card>

      {/* ── Table ── */}
      <Card>
        <Table<AdminOrderRow>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          size="small"
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, ps) => { setPage(p); setPageSize(ps ?? 20) },
          }}
          onRow={(record) => ({ onClick: () => void openDrawer(record), style: { cursor: 'pointer' } })}
        />
      </Card>

      {/* ── Drawer ── */}
      <Drawer
        title={selected ? `Заказ #${selected.id}` : 'Заказ'}
        width={460}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setSelected(null) }}
      >
        {selected && (
          <Spin spinning={drawerLoading}>
            <div className="ag-info-sect">
              <div className="ag-info-sect-title">Основное</div>
              <div className="ag-info-row">
                <span className="k">Статус</span>
                <span className="v">{statusTag(selected.status)}</span>
              </div>
              <div className="ag-info-row">
                <span className="k">Сумма</span>
                <span className="v">
                  {parseFloat(selected.amount).toLocaleString('ru-RU')} ₽
                </span>
              </div>
              <div className="ag-info-row">
                <span className="k">Пользователь</span>
                <span className="v">#{selected.user_id}</span>
              </div>
              <div className="ag-info-row">
                <span className="k">Тариф</span>
                <span className="v">{tariffTag(selected.tariff.code)} {selected.tariff.name}</span>
              </div>
              <div className="ag-info-row">
                <span className="k">Отчёт готов</span>
                <span className="v">
                  {selected.report_ready
                    ? <span className="ag-tag ag-tag-green">да</span>
                    : <span className="ag-tag ag-tag-gray">нет</span>}
                </span>
              </div>
            </div>

            <div className="ag-info-sect">
              <div className="ag-info-sect-title">Временные метки</div>
              <div className="ag-info-row">
                <span className="k">Создан</span>
                <span className="v">{new Date(selected.created_at).toLocaleString('ru-RU')}</span>
              </div>
              <div className="ag-info-row">
                <span className="k">Обновлён</span>
                <span className="v">{new Date(selected.updated_at).toLocaleString('ru-RU')}</span>
              </div>
            </div>

            <Space wrap style={{ marginTop: 8 }}>
              <Button type="primary" size="small" onClick={() => void handleRetry()}>
                Перезапустить отчёт
              </Button>
              <Button size="small" onClick={() => void downloadOrderPdf(selected.id).catch(() => message.error('PDF недоступен'))}>
                Скачать PDF
              </Button>
              <Button size="small" onClick={() => void downloadOrderChart(selected.id).catch(() => message.error('PNG недоступен'))}>
                Скачать PNG
              </Button>
              <Button danger size="small" onClick={handleRefund}>
                Возврат
              </Button>
            </Space>
          </Spin>
        )}
      </Drawer>
    </>
  )
}
