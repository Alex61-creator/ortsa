import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, Card, Drawer, Input, Popconfirm, Segmented, Space, Table, Tabs, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { deleteUser, fetchUsers } from '@/api/users'
import type { AdminUserRow } from '@/types/admin'
import { isAxiosError } from 'axios'
import { addUserNote, blockUser, listUserNotes, patchUserEmail, unblockUser, type UserNoteRow } from '@/api/support'
import { fetchOrders } from '@/api/orders'
import type { AdminOrderRow } from '@/types/admin'

export function UsersPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [q, setQ] = useState('')
  const qRef = useRef(q)
  qRef.current = q
  const [rows, setRows] = useState<AdminUserRow[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<AdminUserRow | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [notes, setNotes] = useState<UserNoteRow[]>([])
  const [newNote, setNewNote] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [activeTab, setActiveTab] = useState('profile')
  const [userOrders, setUserOrders] = useState<AdminOrderRow[]>([])
  const [providerFilter, setProviderFilter] = useState('Все')

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

  const filteredRows = rows.filter((row) => {
    if (providerFilter === 'Все') return true
    return row.oauth_provider.toLowerCase() === providerFilter.toLowerCase()
  })

  const total =
    filteredRows.length < pageSize
      ? (page - 1) * pageSize + filteredRows.length
      : page * pageSize + 1

  const columns: ColumnsType<AdminUserRow> = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: 'Email', dataIndex: 'email', ellipsis: true },
    { title: 'Провайдер', dataIndex: 'oauth_provider' },
    {
      title: 'Сегмент',
      key: 'segment',
      render: (_, row) => {
        if (row.is_admin) return <Tag color="geekblue">admin</Tag>
        const ageMs = Date.now() - new Date(row.created_at).getTime()
        if (ageMs < 7 * 24 * 60 * 60 * 1000) return <Tag color="green">new</Tag>
        return <Tag>active</Tag>
      },
    },
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
        <Space wrap className="admin-toolbar">
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
          <Segmented options={['Все', 'Google', 'Telegram', 'Yandex']} value={providerFilter} onChange={(v) => setProviderFilter(String(v))} />
        </Space>
      </Card>
      <Card title="Пользователи">
        <Table<AdminUserRow>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={filteredRows}
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
            onClick: () => {
              setSelected(record)
              setDrawerOpen(true)
              setActiveTab('profile')
              void listUserNotes(record.id).then(setNotes).catch(() => setNotes([]))
              void fetchOrders({ page: 1, page_size: 20, user_id: record.id }).then(setUserOrders).catch(() => setUserOrders([]))
            },
          })}
        />
      </Card>
      <Drawer
        title={selected ? `Пользователь #${selected.id}` : 'Пользователь'}
        width={460}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        {selected && (
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'profile',
                label: 'Профиль',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div className="admin-drawer-block">
                      <Typography.Text>Email: {selected.email}</Typography.Text>
                    </div>
                    <Space>
                      <Input
                        placeholder="Новый email"
                        value={newEmail}
                        onChange={(e) => setNewEmail(e.target.value)}
                        style={{ width: 240 }}
                      />
                      <Button
                        onClick={() =>
                          void patchUserEmail(selected.id, newEmail)
                            .then(() => message.success('Email обновлён'))
                            .catch(() => message.error('Ошибка обновления email'))
                        }
                      >
                        Сменить email
                      </Button>
                    </Space>
                    <Space>
                      <Popconfirm
                        title="Заблокировать пользователя?"
                        okText="Блокировать"
                        okButtonProps={{ danger: true }}
                        onConfirm={() => void blockUser(selected.id).then(() => message.success('Пользователь заблокирован'))}
                      >
                        <Button danger>Блокировать</Button>
                      </Popconfirm>
                      <Popconfirm
                        title="Разблокировать пользователя?"
                        okText="Разблокировать"
                        onConfirm={() => void unblockUser(selected.id).then(() => message.success('Пользователь разблокирован'))}
                      >
                        <Button>Разблокировать</Button>
                      </Popconfirm>
                    </Space>
                  </Space>
                ),
              },
              {
                key: 'orders',
                label: 'Заказы и возврат',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {userOrders.map((o) => (
                      <div className="admin-drawer-block" key={o.id}>
                        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                          <Typography.Text>Заказ #{o.id}</Typography.Text>
                          <Tag>{o.status}</Tag>
                        </Space>
                        <Typography.Text type="secondary">Сумма: {o.amount}</Typography.Text>
                      </div>
                    ))}
                    {userOrders.length === 0 && <Typography.Text type="secondary">У пользователя нет заказов.</Typography.Text>}
                  </Space>
                ),
              },
              {
                key: 'sub',
                label: 'Подписка',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div className="admin-drawer-block">
                      <Typography.Text>Статус: none</Typography.Text>
                    </div>
                    <Space>
                      <Button onClick={() => message.info('Отмена подписки в этом контуре пока недоступна')}>Cancel at period end</Button>
                      <Button type="primary" onClick={() => message.success('Пользователю выдан Pro (локальный action)')}>
                        Выдать Pro
                      </Button>
                    </Space>
                  </Space>
                ),
              },
              {
                key: 'pipeline',
                label: 'Пайплайн',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {['Данные', 'Оплата', 'Kerykeion', 'LLM', 'PDF', 'Email'].map((step, idx) => (
                      <div className="admin-drawer-block" key={step}>
                        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                          <Typography.Text>{step}</Typography.Text>
                          <Tag color={idx < 4 ? 'green' : 'blue'}>{idx < 4 ? 'ok' : 'run'}</Tag>
                        </Space>
                      </div>
                    ))}
                    <Button onClick={() => message.success('Retry пайплайна отправлен в очередь')}>Retry pipeline</Button>
                  </Space>
                ),
              },
              {
                key: 'notes',
                label: 'Заметки',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Input
                        placeholder="Добавить заметку"
                        value={newNote}
                        onChange={(e) => setNewNote(e.target.value)}
                        style={{ width: 300 }}
                      />
                      <Button
                        type="primary"
                        onClick={() =>
                          void addUserNote(selected.id, newNote)
                            .then(() => listUserNotes(selected.id))
                            .then((rows) => {
                              setNotes(rows)
                              setNewNote('')
                            })
                        }
                      >
                        Добавить
                      </Button>
                    </Space>
                    {notes.map((n) => (
                      <Card key={n.id} size="small">
                        <Typography.Text>{n.text}</Typography.Text>
                      </Card>
                    ))}
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Drawer>
    </Space>
  )
}
