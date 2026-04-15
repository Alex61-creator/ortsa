import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  Card,
  Drawer,
  Input,
  InputNumber,
  Popconfirm,
  Segmented,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { deleteUser, fetchUsers, fetchSynastryOverride, patchSynastryOverride, fetchUserSynastryReports, deleteUserSynastryReport } from '@/api/users'
import type { AdminUserRow, AdminSynastryReportRow, SynastryOverrideRow } from '@/types/admin'
import { isAxiosError } from 'axios'
import { addUserNote, blockUser, listUserNotes, patchUserEmail, unblockUser, type UserNoteRow } from '@/api/support'
import { fetchOrders } from '@/api/orders'
import type { AdminOrderRow } from '@/types/admin'
import dayjs from 'dayjs'

// ── Вкладка Синастрия ─────────────────────────────────────────────────────────

function SynastryTab({ userId }: { userId: number }) {
  const [override, setOverride] = useState<SynastryOverrideRow | null>(null)
  const [reports, setReports] = useState<AdminSynastryReportRow[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [noteValue, setNoteValue] = useState('')
  const [freeCount, setFreeCount] = useState(0)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchSynastryOverride(userId),
      fetchUserSynastryReports(userId),
    ])
      .then(([ov, reps]) => {
        setOverride(ov)
        setNoteValue(ov.admin_note ?? '')
        setFreeCount(ov.free_synastries_granted)
        setReports(reps)
      })
      .catch(() => message.error('Не удалось загрузить данные синастрии'))
      .finally(() => setLoading(false))
  }, [userId])

  const save = async (patch: Parameters<typeof patchSynastryOverride>[1]) => {
    setSaving(true)
    try {
      const updated = await patchSynastryOverride(userId, patch)
      setOverride(updated)
      setFreeCount(updated.free_synastries_granted)
      message.success('Сохранено')
    } catch {
      message.error('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteReport = async (reportId: number) => {
    try {
      await deleteUserSynastryReport(userId, reportId)
      setReports((prev) => prev.filter((r) => r.id !== reportId))
      message.success('Синастрия удалена')
    } catch {
      message.error('Не удалось удалить')
    }
  }

  function statusTag(s: string) {
    switch (s) {
      case 'completed': return <Tag color="green">Готово</Tag>
      case 'processing': return <Tag color="blue">Генерация</Tag>
      case 'pending':    return <Tag color="orange">Ожидание</Tag>
      case 'failed':     return <Tag color="red">Ошибка</Tag>
      default: return <Tag>{s}</Tag>
    }
  }

  if (loading) return <Typography.Text type="secondary">Загрузка...</Typography.Text>

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">

      {/* ── Override: включить/выключить ── */}
      <div className="admin-drawer-block">
        <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
          Доступ к синастрии
        </Typography.Text>
        <Space align="center">
          <Switch
            checked={override?.synastry_enabled ?? false}
            loading={saving}
            onChange={(checked) => void save({ synastry_enabled: checked })}
          />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {override?.synastry_enabled
              ? 'Включено (независимо от тарифа)'
              : 'По тарифу (стандартно)'}
          </Typography.Text>
        </Space>
      </div>

      {/* ── Дополнительные бесплатные синастрии ── */}
      <div className="admin-drawer-block">
        <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
          Дополнительные бесплатные синастрии
        </Typography.Text>
        <Space>
          <InputNumber
            min={0}
            max={999}
            value={freeCount}
            onChange={(v) => setFreeCount(v ?? 0)}
            style={{ width: 100 }}
          />
          <Button
            type="primary"
            loading={saving}
            onClick={() => void save({ free_synastries_granted: freeCount })}
          >
            Сохранить
          </Button>
        </Space>
        <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 4 }}>
          Добавляется к тарифным лимитам (для подписок не учитывается — там безлимит)
        </div>
      </div>

      {/* ── Заметка администратора ── */}
      <div className="admin-drawer-block">
        <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
          Внутренняя заметка
        </Typography.Text>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input.TextArea
            value={noteValue}
            onChange={(e) => setNoteValue(e.target.value)}
            rows={2}
            placeholder="Причина выдачи доступа, дата и т.п."
          />
          <Button
            loading={saving}
            onClick={() => void save({ admin_note: noteValue || null })}
          >
            Сохранить заметку
          </Button>
        </Space>
      </div>

      {/* ── Синастрии пользователя ── */}
      <div>
        <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
          Синастрии ({reports.length})
        </Typography.Text>

        {reports.length === 0 ? (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            У пользователя нет синастрий
          </Typography.Text>
        ) : (
          reports.map((r) => (
            <div key={r.id} className="admin-drawer-block" style={{ marginBottom: 8 }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <div>
                  <Typography.Text strong style={{ fontSize: 13 }}>
                    {r.person1_name ?? `#${r.natal_data_id_1}`} ✦ {r.person2_name ?? `#${r.natal_data_id_2}`}
                  </Typography.Text>
                  <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 2 }}>
                    ID #{r.id} · Генераций: {r.generation_count} · {dayjs(r.created_at).format('DD.MM.YYYY')}
                    {r.pdf_ready && <Tag color="green" style={{ marginLeft: 6, fontSize: 10 }}>PDF готов</Tag>}
                  </div>
                </div>
                <Space>
                  {statusTag(r.status)}
                  <Popconfirm
                    title="Удалить синастрию?"
                    okText="Удалить"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => void handleDeleteReport(r.id)}
                  >
                    <Button danger size="small">Удалить</Button>
                  </Popconfirm>
                </Space>
              </Space>
            </div>
          ))
        )}
      </div>
    </Space>
  )
}

// ── Основная страница ─────────────────────────────────────────────────────────

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
      title: 'Создан',
      dataIndex: 'created_at',
      render: (t: string) => new Date(t).toLocaleString('ru-RU'),
    },
    {
      title: '',
      key: 'actions',
      width: 100,
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
          <Segmented
            options={['Все', 'Google', 'Telegram', 'Yandex']}
            value={providerFilter}
            onChange={(v) => setProviderFilter(String(v))}
          />
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
              void fetchOrders({ page: 1, page_size: 20, user_id: record.id })
                .then(setUserOrders)
                .catch(() => setUserOrders([]))
            },
          })}
        />
      </Card>

      <Drawer
        title={selected ? `Пользователь #${selected.id} — ${selected.email ?? 'без email'}` : 'Пользователь'}
        width={500}
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
                        onConfirm={() =>
                          void blockUser(selected.id).then(() =>
                            message.success('Пользователь заблокирован')
                          )
                        }
                      >
                        <Button danger>Блокировать</Button>
                      </Popconfirm>
                      <Popconfirm
                        title="Разблокировать пользователя?"
                        okText="Разблокировать"
                        onConfirm={() =>
                          void unblockUser(selected.id).then(() =>
                            message.success('Пользователь разблокирован')
                          )
                        }
                      >
                        <Button>Разблокировать</Button>
                      </Popconfirm>
                    </Space>
                  </Space>
                ),
              },
              {
                key: 'orders',
                label: 'Заказы',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {userOrders.map((o) => (
                      <div className="admin-drawer-block" key={o.id}>
                        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                          <Typography.Text>Заказ #{o.id}</Typography.Text>
                          <Tag>{o.status}</Tag>
                        </Space>
                        <Typography.Text type="secondary">
                          {o.tariff?.name ?? '—'} · {o.amount} ₽
                        </Typography.Text>
                      </div>
                    ))}
                    {userOrders.length === 0 && (
                      <Typography.Text type="secondary">Нет заказов.</Typography.Text>
                    )}
                  </Space>
                ),
              },
              {
                key: 'synastry',
                label: 'Синастрия',
                children: <SynastryTab userId={selected.id} />,
              },
              {
                key: 'sub',
                label: 'Подписка',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div className="admin-drawer-block">
                      <Typography.Text>Статус: —</Typography.Text>
                    </div>
                    <Space>
                      <Button
                        onClick={() =>
                          message.info('Отмена подписки в этом контуре пока недоступна')
                        }
                      >
                        Cancel at period end
                      </Button>
                      <Button
                        type="primary"
                        onClick={() =>
                          message.success('Пользователю выдан Pro (локальный action)')
                        }
                      >
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
                    <Button onClick={() => message.success('Retry пайплайна отправлен в очередь')}>
                      Retry pipeline
                    </Button>
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
                        style={{ width: 280 }}
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
