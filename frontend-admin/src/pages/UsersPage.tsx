import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  Card,
  Drawer,
  Input,
  Modal,
  Popconfirm,
  Segmented,
  Space,
  Spin,
  Table,
  Tabs,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { deleteUser, fetchUsers } from '@/api/users'
import type { AdminOrderRow, AdminUserRow } from '@/types/admin'
import { isAxiosError } from 'axios'
import {
  addUserNote,
  blockUser,
  listUserNotes,
  patchUserEmail,
  unblockUser,
  type UserNoteRow,
} from '@/api/support'
import { fetchOrders, postRefund } from '@/api/orders'

/* ── tag helpers ── */
const planTagClass: Record<string, string> = {
  pro: 'ag-tag-purple',
  report: 'ag-tag-blue',
  bundle: 'ag-tag-amber',
  free: 'ag-tag-gray',
}

function PlanTag({ code, name }: { code: string | null; name: string | null }) {
  if (!name) return <span className="ag-tag ag-tag-gray">—</span>
  const cls = code ? (planTagClass[code.toLowerCase()] ?? 'ag-tag-gray') : 'ag-tag-gray'
  return <span className={`ag-tag ${cls}`}>{name}</span>
}

function SegTag({ s }: { s: string }) {
  if (s === 'new')      return <span className="ag-tag ag-tag-green">🟢 new</span>
  if (s === 'active')   return <span className="ag-tag ag-tag-blue">active</span>
  if (s === 'admin')    return <span className="ag-tag ag-tag-purple">admin</span>
  return <span className="ag-tag ag-tag-gray">{s}</span>
}

function statusColor(s: string) {
  if (s === 'completed') return 'var(--ag-success)'
  if (s === 'failed')    return 'var(--ag-danger)'
  if (s === 'refunded')  return 'var(--ag-muted)'
  if (s === 'paid')      return 'var(--ag-primary)'
  return 'var(--ag-muted)'
}

/* ── pipeline: derive step statuses from order status ── */
const STEPS = ['Данные', 'Оплата', 'Kerykeion', 'LLM', 'PDF', 'Email']

function getStepClass(step: number, status: string, reportReady: boolean): string {
  const s = status.toLowerCase()
  if (s === 'pending') return step === 0 ? 'run' : 'pend'
  if (s === 'failed_to_init_payment') return step === 0 ? 'ok' : step === 1 ? 'fail' : 'pend'
  if (s === 'paid') {
    if (step === 0 || step === 1) return 'ok'
    if (step === 2) return 'run'
    return 'pend'
  }
  if (s === 'processing') {
    if (step <= 1) return 'ok'
    if (step === 2 || step === 3) return 'run'
    return 'pend'
  }
  if (s === 'completed') {
    if (step <= 3) return 'ok'
    return reportReady ? 'ok' : 'run'
  }
  if (s === 'failed') {
    if (step <= 1) return 'ok'
    if (step === 2) return 'fail'
    return 'pend'
  }
  if (s === 'refunded') return step <= 1 ? 'ok' : 'pend'
  return 'pend'
}

function PipelineTab({ orders }: { orders: AdminOrderRow[] }) {
  const order = orders[0]
  if (!order)
    return <div className="admin-empty">У пользователя нет заказов для отображения пайплайна.</div>
  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
        }}
      >
        <span style={{ fontSize: 12, color: 'var(--ag-muted)' }}>
          Последний заказ #{order.id} — статус:{' '}
          <strong style={{ color: statusColor(order.status) }}>{order.status}</strong>
        </span>
      </div>
      <div className="ag-pipe-track">
        {STEPS.map((step, i) => {
          const cls = getStepClass(i, order.status, order.report_ready)
          const icon = cls === 'ok' ? '✓' : cls === 'fail' ? '✕' : cls === 'run' ? '…' : String(i + 1)
          return (
            <div key={step} className={`ag-pipe-step ${cls}`}>
              <div className="ag-pipe-circ">{icon}</div>
              <div className="ag-pipe-lbl">{step}</div>
            </div>
          )
        })}
      </div>
      {order.status === 'failed' && (
        <div
          style={{
            marginTop: 12,
            padding: '10px 12px',
            background: 'var(--ag-danger-l)',
            border: '1px solid rgba(255,77,79,.3)',
            borderRadius: 'var(--ag-r)',
            fontSize: 12,
            color: 'var(--ag-danger)',
          }}
        >
          Генерация отчёта завершилась ошибкой. Перезапустите из раздела «Заказы».
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════ */
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
      const data = await fetchUsers({ page, page_size: pageSize, q: qRef.current.trim() || undefined })
      setRows(data)
    } catch {
      message.error('Не удалось загрузить пользователей')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  useEffect(() => { void load() }, [load])

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

  const openDrawer = (record: AdminUserRow) => {
    setSelected(record)
    setDrawerOpen(true)
    setActiveTab('profile')
    setNewEmail('')
    void listUserNotes(record.id).then(setNotes).catch(() => setNotes([]))
    void fetchOrders({ page: 1, page_size: 20, user_id: record.id })
      .then(setUserOrders)
      .catch(() => setUserOrders([]))
  }

  const filteredRows = rows.filter((r) =>
    providerFilter === 'Все' ? true : r.oauth_provider.toLowerCase() === providerFilter.toLowerCase()
  )

  const total =
    filteredRows.length < pageSize
      ? (page - 1) * pageSize + filteredRows.length
      : page * pageSize + 1

  const getSeg = (r: AdminUserRow) => {
    if (r.is_admin) return 'admin'
    const ageMs = Date.now() - new Date(r.created_at).getTime()
    if (ageMs < 7 * 24 * 60 * 60 * 1000) return 'new'
    return 'active'
  }

  const columns: ColumnsType<AdminUserRow> = [
    {
      title: 'Пользователь',
      key: 'user',
      ellipsis: true,
      render: (_, r) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: '50%',
              background: 'var(--ag-primary-l)',
              color: 'var(--ag-primary)',
              fontSize: 11,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {r.email.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div style={{ fontWeight: 500, fontSize: 13 }}>{r.email}</div>
            <div style={{ fontSize: 11, color: 'var(--ag-muted)' }}>{r.oauth_provider}</div>
          </div>
        </div>
      ),
    },
    {
      title: 'Тариф',
      key: 'plan',
      width: 120,
      render: (_, r) => <PlanTag code={r.latest_tariff_code} name={r.latest_tariff_name} />,
    },
    {
      title: 'LTV',
      key: 'ltv',
      width: 100,
      render: (_, r) => {
        const v = parseFloat(r.total_spent)
        return (
          <span style={{ fontWeight: 500, color: v > 0 ? 'var(--ag-primary)' : 'var(--ag-muted)' }}>
            {v > 0 ? `${v.toLocaleString('ru-RU')} ₽` : '—'}
          </span>
        )
      },
    },
    {
      title: 'Заказов',
      dataIndex: 'orders_count',
      width: 80,
      render: (v: number) => v || '—',
    },
    {
      title: 'Посл. заказ',
      key: 'last',
      width: 120,
      render: (_, r) =>
        r.last_order_at
          ? new Date(r.last_order_at).toLocaleDateString('ru-RU')
          : '—',
    },
    {
      title: 'Регистрация',
      dataIndex: 'created_at',
      width: 120,
      render: (t: string) => new Date(t).toLocaleDateString('ru-RU'),
    },
    {
      title: 'Сегмент',
      key: 'seg',
      width: 90,
      render: (_, r) => <SegTag s={getSeg(r)} />,
    },
    {
      title: 'Статус',
      key: 'status',
      width: 90,
      render: (_, r) =>
        r.blocked ? (
          <span className="ag-tag ag-tag-red">🚫 Блок</span>
        ) : (
          <span className="ag-tag ag-tag-green">Активен</span>
        ),
    },
    {
      title: '',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Popconfirm
          title="Удалить пользователя и все данные?"
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
        <div className="admin-toolbar">
          <Input
            placeholder="Поиск по email…"
            style={{ width: 260 }}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onPressEnter={() => { setPage(1); void load() }}
          />
          <Button type="primary" onClick={() => { setPage(1); void load() }}>
            Обновить
          </Button>
          <Segmented
            options={['Все', 'Google', 'Telegram', 'Yandex']}
            value={providerFilter}
            onChange={(v) => setProviderFilter(String(v))}
          />
          <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--ag-muted)' }}>
            {filteredRows.length} пользователей
          </span>
        </div>
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
            onChange: (p, ps) => { setPage(p); setPageSize(ps ?? 20) },
          }}
          onRow={(record) => ({ onClick: () => openDrawer(record) })}
        />
      </Card>

      {/* ── User Drawer ── */}
      <Drawer
        title={
          selected && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: '50%',
                  background: 'var(--ag-primary-l)',
                  color: 'var(--ag-primary)',
                  fontSize: 14,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {selected.email.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <div style={{ fontWeight: 500 }}>{selected.email}</div>
                <div style={{ fontSize: 11, color: 'var(--ag-muted)', fontWeight: 400 }}>
                  #{selected.id} · {selected.oauth_provider}
                </div>
              </div>
              {selected.blocked && <span className="ag-tag ag-tag-red">🚫 Заблокирован</span>}
            </div>
          )
        }
        width={500}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setSelected(null) }}
        footer={
          selected && (
            <div style={{ display: 'flex', gap: 8 }}>
              <Button
                size="small"
                style={{ background: 'var(--ag-warning-l)', color: '#874d00', borderColor: 'var(--ag-warning-b)' }}
                onClick={() =>
                  void blockUser(selected.id)
                    .then(() => { message.success('Пользователь заблокирован'); void load() })
                    .catch(() => message.error('Ошибка блокировки'))
                }
              >
                🚫 Заблокировать
              </Button>
              <Button
                size="small"
                onClick={() =>
                  void unblockUser(selected.id)
                    .then(() => { message.success('Пользователь разблокирован'); void load() })
                    .catch(() => message.error('Ошибка разблокировки'))
                }
              >
                Разблокировать
              </Button>
              <Popconfirm
                title="Удалить аккаунт безвозвратно?"
                okText="Удалить"
                okButtonProps={{ danger: true }}
                onConfirm={() => {
                  void handleDelete(selected.id)
                  setDrawerOpen(false)
                }}
              >
                <Button danger size="small">
                  Удалить аккаунт
                </Button>
              </Popconfirm>
              <Button size="small" style={{ marginLeft: 'auto' }} onClick={() => setDrawerOpen(false)}>
                Закрыть
              </Button>
            </div>
          )
        }
      >
        {selected && (
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="small"
            items={[
              /* ── Профиль ── */
              {
                key: 'profile',
                label: 'Профиль',
                children: (
                  <div>
                    <div className="ag-info-sect">
                      <div className="ag-info-sect-title">Данные</div>
                      <div className="ag-info-row">
                        <span className="k">Email</span>
                        <span className="v">{selected.email}</span>
                      </div>
                      <div className="ag-info-row">
                        <span className="k">Провайдер</span>
                        <span className="v">{selected.oauth_provider}</span>
                      </div>
                      <div className="ag-info-row">
                        <span className="k">Тариф</span>
                        <span className="v">
                          <PlanTag code={selected.latest_tariff_code} name={selected.latest_tariff_name} />
                        </span>
                      </div>
                      <div className="ag-info-row">
                        <span className="k">Сегмент</span>
                        <span className="v"><SegTag s={getSeg(selected)} /></span>
                      </div>
                      <div className="ag-info-row">
                        <span className="k">Регистрация</span>
                        <span className="v">{new Date(selected.created_at).toLocaleString('ru-RU')}</span>
                      </div>
                      <div className="ag-info-row">
                        <span className="k">Последний заказ</span>
                        <span className="v">
                          {selected.last_order_at
                            ? new Date(selected.last_order_at).toLocaleDateString('ru-RU')
                            : '—'}
                        </span>
                      </div>
                    </div>

                    <div className="ag-info-sect">
                      <div className="ag-info-sect-title">Финансы</div>
                      <div className="ag-info-row">
                        <span className="k">LTV</span>
                        <span className="v" style={{ color: 'var(--ag-primary)', fontSize: 16 }}>
                          {parseFloat(selected.total_spent) > 0
                            ? `${parseFloat(selected.total_spent).toLocaleString('ru-RU')} ₽`
                            : '—'}
                        </span>
                      </div>
                      <div className="ag-info-row">
                        <span className="k">Заказов</span>
                        <span className="v">{selected.orders_count || '—'}</span>
                      </div>
                    </div>

                    <div className="ag-info-sect">
                      <div className="ag-info-sect-title">Сменить email</div>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <Input
                          placeholder="Новый email"
                          value={newEmail}
                          onChange={(e) => setNewEmail(e.target.value)}
                          style={{ flex: 1 }}
                        />
                        <Button
                          type="primary"
                          size="small"
                          onClick={() =>
                            void patchUserEmail(selected.id, newEmail)
                              .then(() => { message.success('Email обновлён'); setNewEmail(''); void load() })
                              .catch(() => message.error('Ошибка обновления email'))
                          }
                        >
                          OK
                        </Button>
                      </div>
                    </div>
                  </div>
                ),
              },

              /* ── Заказы & Возврат ── */
              {
                key: 'orders',
                label: 'Заказы & Возврат',
                children: (
                  <div>
                    {userOrders.length === 0 ? (
                      <div className="admin-empty">У пользователя нет заказов.</div>
                    ) : (
                      userOrders.map((o) => (
                        <div key={o.id} className="admin-drawer-block" style={{ marginBottom: 8 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                            <span style={{ fontWeight: 500 }}>Заказ #{o.id}</span>
                            <span className={`ag-tag ${
                              o.status === 'completed' ? 'ag-tag-green'
                              : o.status === 'failed' ? 'ag-tag-red'
                              : o.status === 'paid' ? 'ag-tag-blue'
                              : o.status === 'refunded' ? 'ag-tag-gray'
                              : 'ag-tag-amber'
                            }`}>{o.status}</span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--ag-muted)', marginBottom: 8 }}>
                            {o.tariff.name} · {o.amount} ₽ · {new Date(o.created_at).toLocaleDateString('ru-RU')}
                          </div>
                          {(o.status === 'paid' || o.status === 'completed') && (
                            <Button
                              danger
                              size="small"
                              onClick={() => {
                                const ref: { current: string } = { current: '' }
                                Modal.confirm({
                                  title: `Возврат по заказу #${o.id}`,
                                  content: (
                                    <div>
                                      <p style={{ marginBottom: 8, fontSize: 13 }}>
                                        Полный возврат — оставьте поле пустым. Частичный — укажите сумму.
                                      </p>
                                      <Input
                                        placeholder={`Сумма (макс. ${o.amount} ₽)`}
                                        onChange={(e) => { ref.current = e.target.value }}
                                      />
                                    </div>
                                  ),
                                  okText: 'Вернуть деньги',
                                  okButtonProps: { danger: true },
                                  onOk: async () => {
                                    await postRefund(o.id, ref.current.trim() || undefined)
                                    message.success('Возврат инициирован')
                                    void fetchOrders({ page: 1, page_size: 20, user_id: selected.id })
                                      .then(setUserOrders)
                                  },
                                })
                              }}
                            >
                              Возврат
                            </Button>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                ),
              },

              /* ── Подписка ── */
              {
                key: 'sub',
                label: 'Подписка',
                children: (
                  <div>
                    {(() => {
                      const proOrder = userOrders.find(
                        (o) =>
                          o.tariff.billing_type === 'subscription' &&
                          (o.status === 'paid' || o.status === 'completed')
                      )
                      if (!proOrder)
                        return (
                          <div
                            style={{
                              padding: '14px',
                              background: 'var(--ag-card-soft)',
                              border: '1px solid var(--ag-border)',
                              borderRadius: 'var(--ag-r)',
                              color: 'var(--ag-muted)',
                              fontSize: 13,
                            }}
                          >
                            Активной подписки нет.
                          </div>
                        )
                      return (
                        <div
                          style={{
                            background: 'var(--ag-purple-l)',
                            border: '1px solid rgba(114,46,209,.25)',
                            borderRadius: 'var(--ag-r)',
                            padding: 14,
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 5,
                                background: 'var(--ag-success-l)',
                                border: '1px solid var(--ag-success-b)',
                                borderRadius: 20,
                                padding: '3px 10px',
                                fontSize: 11,
                                color: '#389e0d',
                                fontWeight: 500,
                              }}
                            >
                              ● Активна
                            </span>
                          </div>
                          <div className="ag-info-row">
                            <span className="k">Тариф</span>
                            <span className="v">{proOrder.tariff.name}</span>
                          </div>
                          <div className="ag-info-row">
                            <span className="k">Сумма</span>
                            <span className="v">{proOrder.amount} ₽</span>
                          </div>
                          <div className="ag-info-row">
                            <span className="k">Статус</span>
                            <span className="v">{proOrder.status}</span>
                          </div>
                          <div className="ag-info-row">
                            <span className="k">Дата заказа</span>
                            <span className="v">{new Date(proOrder.created_at).toLocaleDateString('ru-RU')}</span>
                          </div>
                          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                            <Button
                              danger
                              size="small"
                              onClick={() => message.info('Отмена подписки: используйте раздел Заказы → Возврат')}
                            >
                              Отменить подписку
                            </Button>
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                ),
              },

              /* ── Пайплайн ── */
              {
                key: 'pipeline',
                label: 'Пайплайн',
                children: <PipelineTab orders={userOrders} />,
              },

              /* ── Заметки ── */
              {
                key: 'notes',
                label: 'Заметки',
                children: (
                  <div>
                    <div style={{ marginBottom: 12 }}>
                      <Input.TextArea
                        rows={3}
                        placeholder="Добавить заметку (видно только администраторам)…"
                        value={newNote}
                        onChange={(e) => setNewNote(e.target.value)}
                        style={{ marginBottom: 6, resize: 'vertical' }}
                      />
                      <Button
                        type="primary"
                        size="small"
                        onClick={() =>
                          void addUserNote(selected.id, newNote)
                            .then(() => listUserNotes(selected.id))
                            .then((rows) => { setNotes(rows); setNewNote('') })
                        }
                      >
                        Добавить заметку
                      </Button>
                    </div>
                    {notes.length === 0 ? (
                      <div className="admin-empty">Заметок пока нет.</div>
                    ) : (
                      notes.map((n) => (
                        <div
                          key={n.id}
                          style={{
                            background: 'var(--ag-card-soft)',
                            border: '1px solid var(--ag-border)',
                            borderRadius: 'var(--ag-r)',
                            padding: '10px 12px',
                            marginBottom: 8,
                          }}
                        >
                          <div style={{ fontSize: 11, color: 'var(--ag-text-4)', marginBottom: 4 }}>
                            {new Date(n.created_at).toLocaleString('ru-RU')}
                          </div>
                          <div style={{ fontSize: 13, color: 'var(--ag-text-2)', lineHeight: 1.5 }}>
                            {n.text}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                ),
              },
            ]}
          />
        )}
      </Drawer>
    </Space>
  )
}
