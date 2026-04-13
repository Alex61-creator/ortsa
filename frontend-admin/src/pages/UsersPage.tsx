import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, Card, Input, Popconfirm, Space, Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { deleteUser, fetchUsers } from '@/api/users'
import type { AdminUserRow } from '@/types/admin'
import { isAxiosError } from 'axios'

export function UsersPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [q, setQ] = useState('')
  const qRef = useRef(q)
  qRef.current = q
  const [rows, setRows] = useState<AdminUserRow[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchUsers({
        page,
        page_size: pageSize,
        q: qRef.current.trim() || undefined,
      })
      setRows(data)
    } catch {
      message.error('Не удалось загрузить пользователей')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  useEffect(() => {
    void load()
  }, [load])

  const handleDelete = async (id: number) => {
    try {
      await deleteUser(id)
      message.success('Пользователь удалён')
      void load()
    } catch (e) {
      if (isAxiosError(e) && e.response?.status === 400) {
        const d = e.response?.data as { detail?: string }
        message.error(d?.detail ?? 'Нельзя удалить')
      } else {
        message.error('Ошибка удаления')
      }
    }
  }

  const total =
    rows.length < pageSize
      ? (page - 1) * pageSize + rows.length
      : page * pageSize + 1

  const columns: ColumnsType<AdminUserRow> = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: 'Email', dataIndex: 'email', ellipsis: true },
    { title: 'Провайдер', dataIndex: 'oauth_provider' },
    {
      title: 'Админ',
      dataIndex: 'is_admin',
      render: (v: boolean) => (v ? <Tag color="blue">да</Tag> : <Tag>нет</Tag>),
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      render: (t: string) => new Date(t).toLocaleString('ru-RU'),
    },
    {
      title: '',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Popconfirm
          title="Удалить пользователя и связанные данные?"
          okText="Удалить"
          okButtonProps={{ danger: true }}
          onConfirm={() => void handleDelete(record.id)}
        >
          <Button danger size="small">
            Удалить
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card>
        <Space wrap>
          <Input
            placeholder="Поиск по email"
            style={{ width: 260 }}
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
      <Card title="Пользователи">
        <Table<AdminUserRow>
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
        />
      </Card>
    </Space>
  )
}
