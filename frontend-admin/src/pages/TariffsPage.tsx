import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchTariffs, patchTariff } from '@/api/tariffs'
import type { TariffPatch, TariffRow } from '@/types/admin'
import { fetchTariffHistory, type TariffHistoryRow } from '@/api/tariffHistory'

interface TariffFormValues {
  name: string
  price: string
  price_usd: string
  compare_price_usd: string
  annual_total_usd: string
  retention_days: number
  priority: number
  billing_type: string
  subscription_interval?: string | null
  llm_tier: string
  featuresJson: string
}

const BILLING = [
  { value: 'one_time', label: 'one_time' },
  { value: 'subscription', label: 'subscription' },
]

const LLM = [
  { value: 'free', label: 'free' },
  { value: 'natal_full', label: 'natal_full' },
  { value: 'pro', label: 'pro' },
]

const SUB_INT = [
  { value: 'month', label: 'month' },
  { value: 'year', label: 'year' },
]

export function TariffsPage() {
  const [rows, setRows] = useState<TariffRow[]>([])
  const [history, setHistory] = useState<TariffHistoryRow[]>([])
  const [loading, setLoading] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editing, setEditing] = useState<TariffRow | null>(null)
  const [form] = Form.useForm<TariffFormValues>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchTariffs()
      setRows(data)
      const hist = await fetchTariffHistory()
      setHistory(hist)
    } catch {
      message.error('Не удалось загрузить тарифы')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openEdit = (row: TariffRow) => {
    setEditing(row)
    form.setFieldsValue({
      name: row.name,
      price: row.price,
      price_usd: row.price_usd,
      compare_price_usd: row.compare_price_usd ?? '',
      annual_total_usd: row.annual_total_usd ?? '',
      retention_days: row.retention_days,
      priority: row.priority,
      billing_type: row.billing_type,
      subscription_interval: row.subscription_interval ?? undefined,
      llm_tier: row.llm_tier,
      featuresJson: JSON.stringify(row.features ?? {}, null, 2),
    })
    setEditOpen(true)
  }

  const submitEdit = async () => {
    if (!editing) return
    try {
      const v = await form.validateFields()
      let features: Record<string, unknown> | undefined
      try {
        features = JSON.parse(v.featuresJson || '{}') as Record<string, unknown>
      } catch {
        message.error('Некорректный JSON в поле features')
        return
      }
      const body: TariffPatch = {
        name: v.name,
        price: v.price,
        price_usd: v.price_usd,
        compare_price_usd: v.compare_price_usd?.trim() ? v.compare_price_usd : null,
        annual_total_usd: v.annual_total_usd?.trim() ? v.annual_total_usd : null,
        retention_days: v.retention_days,
        priority: v.priority,
        billing_type: v.billing_type,
        subscription_interval: v.subscription_interval ?? null,
        llm_tier: v.llm_tier,
        features,
      }
      await patchTariff(editing.id, body)
      message.success('Тариф обновлён')
      setEditOpen(false)
      setEditing(null)
      void load()
    } catch {
      /* validation */
    }
  }

  const columns: ColumnsType<TariffRow> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Код', dataIndex: 'code' },
    { title: 'Название', dataIndex: 'name' },
    { title: 'Цена ₽', dataIndex: 'price' },
    { title: 'Тип', dataIndex: 'billing_type', render: (t) => <Tag>{t}</Tag> },
    { title: 'LLM', dataIndex: 'llm_tier' },
    {
      title: '',
      key: 'a',
      width: 100,
      render: (_, row) => (
        <Button type="link" size="small" onClick={() => openEdit(row)}>
          Изменить
        </Button>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div className="admin-page-title">Тарифы</div>
      <Card>
        <Button type="primary" onClick={() => void load()}>
          Обновить
        </Button>
      </Card>
      <Card title="Тарифы">
        <Table<TariffRow>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={false}
        />
      </Card>
      <Card title="История изменений цен">
        <Table<TariffHistoryRow>
          rowKey="id"
          columns={[
            { title: 'Когда', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString('ru-RU') },
            { title: 'Кто', dataIndex: 'actor' },
            { title: 'Тариф', dataIndex: 'tariff_id' },
            {
              title: 'Изменение',
              dataIndex: 'payload',
              render: (v: Record<string, unknown>) => JSON.stringify(v),
            },
          ]}
          dataSource={history}
          pagination={{ pageSize: 10 }}
        />
      </Card>
      <Modal
        title={editing ? `Тариф ${editing.code}` : 'Тариф'}
        open={editOpen}
        onCancel={() => {
          setEditOpen(false)
          setEditing(null)
        }}
        onOk={() => void submitEdit()}
        okText="Сохранить"
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="price" label="Цена ₽" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="price_usd" label="Цена USD (отображение)" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="compare_price_usd" label="compare_price_usd">
            <Input placeholder="пусто = null" />
          </Form.Item>
          <Form.Item name="annual_total_usd" label="annual_total_usd">
            <Input placeholder="пусто = null" />
          </Form.Item>
          <Form.Item name="retention_days" label="retention_days" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="priority" label="priority" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="billing_type" label="billing_type" rules={[{ required: true }]}>
            <Select options={BILLING} />
          </Form.Item>
          <Form.Item name="subscription_interval" label="subscription_interval">
            <Select allowClear options={SUB_INT} placeholder="null" />
          </Form.Item>
          <Form.Item name="llm_tier" label="llm_tier" rules={[{ required: true }]}>
            <Select options={LLM} />
          </Form.Item>
          <Form.Item
            name="featuresJson"
            label="features (JSON)"
            rules={[{ required: true, message: 'Укажите JSON' }]}
          >
            <Input.TextArea rows={6} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
