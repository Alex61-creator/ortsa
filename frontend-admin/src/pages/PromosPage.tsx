import { useEffect, useState } from 'react'
import { Button, Card, DatePicker, Form, Input, InputNumber, Space, Switch, Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { createPromo, fetchPromos, patchPromo } from '@/api/promos'
import type { PromoRow } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

export function PromosPage() {
  const [rows, setRows] = useState<PromoRow[]>([])
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    void fetchPromos()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const columns: ColumnsType<PromoRow> = [
    { title: 'Код', dataIndex: 'code' },
    { title: 'Скидка %', dataIndex: 'discount_percent' },
    { title: 'Использовано', dataIndex: 'used_count' },
    { title: 'Лимит', dataIndex: 'max_uses' },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? 'active' : 'inactive'}</Tag>,
    },
    {
      title: 'Вкл',
      key: 'enabled',
      render: (_, row) => (
        <Switch
          checked={row.is_active}
          onChange={(v) =>
            void patchPromo(row.id, { is_active: v })
              .then(() => {
                message.success('Статус промокода обновлен')
                load()
              })
              .catch((e) => message.error(extractApiErrorMessage(e, 'Не удалось обновить промокод')))
          }
        />
      ),
    },
  ]

  return (
    <>
      <div className="admin-page-title">Промокоды</div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Card title="Новый промокод">
          <Form
            form={form}
            layout="inline"
            onFinish={(v) =>
              void createPromo({
                ...v,
                active_until: v.active_until?.toISOString?.() ?? null,
              })
                .then(() => {
                  message.success('Промокод создан')
                  form.resetFields()
                  load()
                })
                .catch(() => message.error('Не удалось создать промокод'))
            }
          >
            <Form.Item name="code" rules={[{ required: true }]}>
              <Input placeholder="CODE" />
            </Form.Item>
            <Form.Item name="discount_percent" rules={[{ required: true }]}>
              <InputNumber min={1} max={100} placeholder="% скидки" />
            </Form.Item>
            <Form.Item name="max_uses" initialValue={100} rules={[{ required: true }]}>
              <InputNumber min={1} placeholder="Лимит" />
            </Form.Item>
            <Form.Item name="active_until">
              <DatePicker showTime placeholder="Срок действия" />
            </Form.Item>
            <Button htmlType="submit" type="primary">
              Создать
            </Button>
          </Form>
        </Card>
        <Card title="Список">
          <Table rowKey="id" loading={loading} columns={columns} dataSource={rows} pagination={false} />
        </Card>
      </Space>
    </>
  )
}
