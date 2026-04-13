import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  Drawer,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchOrder, fetchOrders, postRefund, postRetryReport } from '@/api/orders'
import { downloadOrderChart, downloadOrderPdf } from '@/api/reports'
import type { AdminOrderRow } from '@/types/admin'
import { isAxiosError } from 'axios'

const { Text } = Typography

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
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [userId, setUserId] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const qRef = useRef(q)
  qRef.current = q
  const [rows, setRows] = useState<AdminOrderRow[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selected, setSelected] = useState<AdminOrderRow | null>(null)
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

  useEffect(() => {
    void load()
  }, [load])

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

  const handleDownloadPdf = async () => {
    if (!selected) return
    try {
      await downloadOrderPdf(selected.id)
      message.success('Скачивание начато')
    } catch {
      message.error('PDF недоступен (нет файла или отчёта)')
    }
  }

  const handleDownloadChart = async () => {
    if (!selected) return
    try {
      await downloadOrderChart(selected.id)
      message.success('Скачивание начато')
    } catch {
      message.error('PNG недоступен')
    }
  }

  const handleRefund = () => {
    if (!selected) return
    const amountRef = { current: '' }
    Modal.confirm({
      title: 'Возврат по заказу',
      content: (
        <div>
          <p>Заказ #{selected.id}. Оставьте сумму пустой для полного возврата или укажите частичную.</p>
          <Input
            placeholder="Сумма (опционально)"
            onChange={(e) => {
              amountRef.current = e.target.value
            }}
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
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: 'Пользователь', dataIndex: 'user_id', width: 100 },
    {
      title: 'Статус',
      dataIndex: 'status',
      render: (s: string) => <Tag>{s}</Tag>,
    },
    { title: 'Сумма', dataIndex: 'amount' },
    {
      title: 'Тариф',
      render: (_, r) => `${r.tariff.code} · ${r.tariff.name}`,
    },
    {
      title: 'Отчёт',
      dataIndex: 'report_ready',
      render: (v: boolean) => (v ? <Tag color="green">готов</Tag> : <Tag>нет</Tag>),
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      render: (t: string) => new Date(t).toLocaleString('ru-RU'),
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card title="Фильтры">
        <Space wrap align="start">
          <Select
            style={{ width: 220 }}
            value={status ?? ''}
            options={STATUS_OPTIONS}
            onChange={(v) => {
              setStatus(v || undefined)
              setPage(1)
            }}
          />
          <Space>
            <Text type="secondary">user_id</Text>
            <InputNumber
              min={1}
              value={userId ?? undefined}
              onChange={(v) => {
                setUserId(typeof v === 'number' ? v : null)
                setPage(1)
              }}
            />
          </Space>
          <Input
            placeholder="ID заказа"
            style={{ width: 120 }}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onPressEnter={() => {
              setPage(1)
              void load()
            }}
          />
          <Button type="primary" onClick={() => void load()}>
            Обновить
          </Button>
        </Space>
      </Card>
      <Card title="Заказы">
        <Table<AdminOrderRow>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps ?? 20)
            },
          }}
          onRow={(record) => ({
            onClick: () => void openDrawer(record),
          })}
        />
      </Card>
      <Drawer
        title={selected ? `Заказ #${selected.id}` : 'Заказ'}
        width={480}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setSelected(null)
        }}
      >
        {selected && (
          <Spin spinning={drawerLoading}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text type="secondary">Статус</Text>
              <div>
                <Tag>{selected.status}</Tag>
              </div>
            </div>
            <div>
              <Text type="secondary">Сумма</Text>
              <div>{selected.amount}</div>
            </div>
            <div>
              <Text type="secondary">Пользователь (user_id)</Text>
              <div>{selected.user_id}</div>
            </div>
            <div>
              <Text type="secondary">Тариф</Text>
              <div>
                {selected.tariff.code} — {selected.tariff.name}
              </div>
            </div>
            <div>
              <Text type="secondary">Отчёт готов</Text>
              <div>{selected.report_ready ? 'да' : 'нет'}</div>
            </div>
            <div>
              <Text type="secondary">Создан / обновлён</Text>
              <div>
                {new Date(selected.created_at).toLocaleString('ru-RU')}
                <br />
                {new Date(selected.updated_at).toLocaleString('ru-RU')}
              </div>
            </div>
            <Space wrap>
              <Button type="primary" onClick={() => void handleRetry()}>
                Перезапустить отчёт
              </Button>
              <Button onClick={() => void handleDownloadPdf()}>Скачать PDF</Button>
              <Button onClick={() => void handleDownloadChart()}>Скачать PNG карты</Button>
              <Button danger onClick={handleRefund}>
                Возврат
              </Button>
            </Space>
          </Space>
          </Spin>
        )}
      </Drawer>
    </Space>
  )
}
