import { useState } from 'react'
import { App, Button, Modal, Select, Spin, Tag, Tooltip } from 'antd'
import {
  DeleteOutlined,
  DownloadOutlined,
  HeartFilled,
  HeartOutlined,
  PlusOutlined,
  ReloadOutlined,
  StarOutlined,
  SyncOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import {
  createSynastry,
  deleteSynastry,
  getSynastryDownloadUrl,
  getSynastryQuota,
  listSynastry,
  purchaseSynastry,
  regenerateSynastry,
  type SynastryOut,
} from '@/api/synastry'
import { listNatalData } from '@/api/natal'

dayjs.extend(relativeTime)

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusTag(s: SynastryOut) {
  switch (s.status) {
    case 'completed': return <Tag color="green">Готово</Tag>
    case 'processing': return <Tag color="blue" icon={<SyncOutlined spin />}>Генерация...</Tag>
    case 'pending':    return <Tag color="orange">Ожидание</Tag>
    case 'failed':     return <Tag color="red">Ошибка</Tag>
    default: return <Tag>{s.status}</Tag>
  }
}

// ── Описание синастрии (всегда отображается вверху) ───────────────────────────

function SynastryDescription() {
  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(201, 110, 140, 0.08) 0%, rgba(22, 119, 255, 0.06) 100%)',
      border: '1px solid rgba(201, 110, 140, 0.25)',
      borderRadius: 16,
      padding: '24px 28px',
      marginBottom: 24,
    }}>
      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Иконка */}
        <div style={{
          width: 56,
          height: 56,
          borderRadius: 16,
          background: 'rgba(201, 110, 140, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <HeartFilled style={{ fontSize: 28, color: '#c96e8c' }} />
        </div>

        <div style={{ flex: 1, minWidth: 240 }}>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: 'var(--ag-text)' }}>
            Синастрия — анализ совместности
          </div>
          <div style={{ fontSize: 14, color: 'var(--ag-text-secondary)', lineHeight: 1.65, marginBottom: 16 }}>
            Синастрия — это астрологический метод исследования взаимоотношений между двумя людьми.
            Сравниваются натальные карты, находятся аспекты между планетами и определяется характер
            взаимодействия: в любви, дружбе, работе или семье.
          </div>

          {/* Для кого */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {[
              { icon: <HeartOutlined />, text: 'Пары и романтические отношения' },
              { icon: <TeamOutlined />, text: 'Деловые партнёры и коллеги' },
              { icon: <StarOutlined />, text: 'Родители и дети' },
            ].map(({ icon, text }) => (
              <div key={text} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 12px',
                background: 'var(--ag-bg-container)',
                border: '1px solid var(--ag-border)',
                borderRadius: 20,
                fontSize: 12,
                color: 'var(--ag-text-secondary)',
              }}>
                <span style={{ color: '#c96e8c' }}>{icon}</span>
                {text}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Баннер для пользователей без доступа ─────────────────────────────────────

function SynastryLockedBanner() {
  return (
    <div style={{ padding: '0 0 24px' }}>
      <SynastryDescription />

      <div style={{
        background: 'var(--ag-bg-container)',
        border: '1px solid var(--ag-border)',
        borderRadius: 16,
        padding: '28px 32px',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🔒</div>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8, color: 'var(--ag-text)' }}>
          Синастрия недоступна на вашем тарифе
        </div>
        <div style={{ fontSize: 14, color: 'var(--ag-text-secondary)', marginBottom: 24, maxWidth: 480, margin: '0 auto 24px' }}>
          Подключите подписку или приобретите набор, чтобы получить доступ
          к анализу совместности двух натальных карт.
        </div>

        {/* Тарифы с синастрией */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 24 }}>
          {[
            { name: 'Набор 3', badge: '1 синастрия', color: '#1677ff' },
            { name: 'Astro Pro (месяц)', badge: 'Безлимит', color: '#52c41a' },
            { name: 'Astro Pro (год)', badge: 'Безлимит', color: '#52c41a' },
          ].map(({ name, badge, color }) => (
            <div key={name} style={{
              padding: '10px 16px',
              background: 'var(--ag-bg)',
              border: `1px solid ${color}40`,
              borderRadius: 12,
              minWidth: 140,
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--ag-text)', marginBottom: 4 }}>{name}</div>
              <div style={{ fontSize: 11, color, fontWeight: 600 }}>{badge}</div>
            </div>
          ))}
        </div>

        <Button type="primary" size="large" href="/order/tariff" style={{ minWidth: 180 }}>
          Выбрать тариф
        </Button>
      </div>
    </div>
  )
}

// ── Основная страница с синастриями ───────────────────────────────────────────

export function SynastryPage() {
  const { message, modal } = App.useApp()
  const qc = useQueryClient()

  const [createOpen, setCreateOpen] = useState(false)
  const [p1Id, setP1Id] = useState<number | null>(null)
  const [p2Id, setP2Id] = useState<number | null>(null)

  const { data: quota, isLoading: quotaLoading } = useQuery({
    queryKey: ['synastry-quota'],
    queryFn: getSynastryQuota,
  })
  const { data: list = [], isLoading: listLoading } = useQuery({
    queryKey: ['synastry'],
    queryFn: listSynastry,
    refetchInterval: (q) => {
      const hasActive = q.state.data?.some(
        (r) => r.status === 'pending' || r.status === 'processing',
      )
      return hasActive ? 5000 : false
    },
  })
  const { data: natalProfiles = [] } = useQuery({
    queryKey: ['natal-data'],
    queryFn: listNatalData,
  })

  const createMut = useMutation({
    mutationFn: () => {
      if (!p1Id || !p2Id) throw new Error('Выберите оба профиля')
      return createSynastry({ natal_data_id_1: p1Id, natal_data_id_2: p2Id })
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['synastry'] })
      void qc.invalidateQueries({ queryKey: ['synastry-quota'] })
      setCreateOpen(false)
      setP1Id(null)
      setP2Id(null)
      message.success('Синастрия создана. Генерация началась...')
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string | { message?: string } } } })?.response?.data?.detail
      const msg = typeof detail === 'object' ? detail?.message : detail
      message.error(msg ?? 'Не удалось создать синастрию')
    },
  })

  const purchaseMut = useMutation({
    mutationFn: purchaseSynastry,
    onSuccess: (data) => {
      // Перенаправляем на страницу оплаты ЮKassa
      window.location.href = data.payment_url
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail ?? 'Не удалось создать платёж')
    },
  })

  const regenMut = useMutation({
    mutationFn: (id: number) => regenerateSynastry(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['synastry'] })
      message.success('Регенерация запущена')
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail ?? 'Не удалось регенерировать')
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteSynastry(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['synastry'] })
      void qc.invalidateQueries({ queryKey: ['synastry-quota'] })
      message.success('Синастрия удалена')
    },
  })

  const confirmDelete = (id: number, names: string) => {
    modal.confirm({
      title: 'Удалить синастрию?',
      content: `«${names}» будет удалена безвозвратно.`,
      okText: 'Удалить',
      okButtonProps: { danger: true },
      onOk: () => deleteMut.mutate(id),
    })
  }

  if (quotaLoading) {
    return (
      <div style={{ padding: 32, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  // Нет доступа — показываем описание + предложение купить
  if (!quota?.has_access) {
    return (
      <div style={{ padding: 24 }}>
        <SynastryLockedBanner />
      </div>
    )
  }

  // ── Определяем состояние кнопки «Создать» ────────────────────────────────
  const canCreate = !quota.is_generating
  const needsPayment = quota.requires_payment
  const repeatPrice = quota.repeat_price
    ? Number(quota.repeat_price).toLocaleString('ru-RU', { maximumFractionDigits: 0 })
    : '190'
  const profileOptions = natalProfiles.map((nd) => ({
    value: nd.id,
    label: `${nd.full_name} · ${nd.birth_place}`,
  }))

  // Текст подписи под заголовком
  function quotaSubtitle() {
    if (quota!.is_unlimited) {
      return (
        <span>
          Безлимитные синастрии
          {quota!.is_generating && (
            <span style={{ marginLeft: 8, color: '#faad14' }}>· Идёт генерация...</span>
          )}
        </span>
      )
    }
    const total = quota!.total_allowed
    const used = quota!.synastries_created
    if (total === -1) {
      return <span>Безлимитные синастрии</span>
    }
    return (
      <span>
        Использовано {used} из {total > 0 ? total : '∞'} включённых
        {quota!.requires_payment && (
          <span style={{ marginLeft: 8, color: '#faad14' }}>
            · Следующая за {repeatPrice} ₽
          </span>
        )}
        {quota!.is_generating && (
          <span style={{ marginLeft: 8, color: '#faad14' }}>· Идёт генерация...</span>
        )}
      </span>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      {/* Описание — всегда видно */}
      <SynastryDescription />

      {/* ── Header ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 20,
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 2 }}>
            <HeartOutlined style={{ marginRight: 8, color: '#c96e8c' }} />
            Мои синастрии
          </div>
          <div style={{ fontSize: 12, color: 'var(--ag-text-secondary)' }}>
            {quotaSubtitle()}
          </div>
        </div>

        {needsPayment ? (
          <Tooltip title={quota.is_generating ? 'Дождитесь завершения текущей генерации' : ''}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={!canCreate}
              loading={purchaseMut.isPending}
              onClick={() => purchaseMut.mutate()}
              style={{ background: canCreate ? '#c96e8c' : undefined, borderColor: canCreate ? '#c96e8c' : undefined }}
            >
              Новая синастрия · {repeatPrice} ₽
            </Button>
          </Tooltip>
        ) : (
          <Tooltip title={quota.is_generating ? 'Дождитесь завершения текущей генерации' : ''}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={!canCreate}
              onClick={() => setCreateOpen(true)}
              style={{ background: canCreate ? '#c96e8c' : undefined, borderColor: canCreate ? '#c96e8c' : undefined }}
            >
              Новая синастрия
            </Button>
          </Tooltip>
        )}
      </div>

      {/* ── Список синастрий ── */}
      {listLoading ? (
        <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div>
      ) : list.length === 0 ? (
        <div className="synastry-empty">
          <HeartOutlined style={{ fontSize: 40, color: 'var(--ag-border)', marginBottom: 12 }} />
          <div style={{ fontSize: 14, color: 'var(--ag-text-secondary)' }}>
            У вас пока нет синастрий.
          </div>
          <div style={{ fontSize: 12, color: 'var(--ag-text-secondary)', marginTop: 4 }}>
            Нажмите «Новая синастрия», выберите два натальных профиля —<br />
            мы рассчитаем совместность и сгенерируем PDF-отчёт.
          </div>
          {canCreate && (
            needsPayment ? (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                style={{ marginTop: 16, background: '#c96e8c', borderColor: '#c96e8c' }}
                loading={purchaseMut.isPending}
                onClick={() => purchaseMut.mutate()}
              >
                Создать синастрию · {repeatPrice} ₽
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                style={{ marginTop: 16, background: '#c96e8c', borderColor: '#c96e8c' }}
                onClick={() => setCreateOpen(true)}
              >
                Создать синастрию
              </Button>
            )
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {list.map((s) => {
            const pairName = `${s.person1_name ?? '?'} ✦ ${s.person2_name ?? '?'}`
            return (
              <div key={s.id} className="synastry-card">
                <div className="synastry-card-header">
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{pairName}</div>
                    <div style={{ fontSize: 12, color: 'var(--ag-text-secondary)', marginTop: 2 }}>
                      Создана {dayjs(s.created_at).format('DD.MM.YYYY')}
                      {s.last_generated_at && ` · Последний отчёт ${dayjs(s.last_generated_at).format('DD.MM.YYYY HH:mm')}`}
                      {` · Генераций: ${s.generation_count}`}
                    </div>
                  </div>
                  {statusTag(s)}
                </div>

                <div className="synastry-card-actions">
                  {/* Download */}
                  {s.pdf_ready && (
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      href={getSynastryDownloadUrl(s.id)}
                      target="_blank"
                    >
                      Скачать PDF
                    </Button>
                  )}

                  {/* Regenerate */}
                  <Tooltip
                    title={
                      s.status === 'processing' || s.status === 'pending'
                        ? 'Идёт генерация...'
                        : 'Перегенерировать с актуальными данными'
                    }
                  >
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      loading={regenMut.isPending && regenMut.variables === s.id}
                      disabled={s.status === 'processing' || s.status === 'pending'}
                      onClick={() => regenMut.mutate(s.id)}
                    >
                      Перегенерировать
                    </Button>
                  </Tooltip>

                  {/* Delete */}
                  <Tooltip title="Удалить синастрию">
                    <Button
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      loading={deleteMut.isPending && deleteMut.variables === s.id}
                      onClick={() => confirmDelete(s.id, pairName)}
                    />
                  </Tooltip>
                </div>

                {/* Подсказка об изменении данных */}
                {s.pdf_ready && (
                  <div style={{
                    fontSize: 11,
                    color: 'var(--ag-text-secondary)',
                    marginTop: 8,
                    paddingTop: 8,
                    borderTop: '1px solid var(--ag-border)',
                  }}>
                    💡 Чтобы обновить отчёт — отредактируйте дату, время или место рождения одного из партнёров
                    в разделе <a href="/dashboard/natal">«Натальные данные»</a>, затем нажмите «Перегенерировать».
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── Модальное окно создания ── */}
      <Modal
        title={
          <span>
            <HeartOutlined style={{ marginRight: 8, color: '#c96e8c' }} />
            Новая синастрия
          </span>
        }
        open={createOpen}
        onCancel={() => { setCreateOpen(false); setP1Id(null); setP2Id(null) }}
        footer={null}
        width={480}
      >
        <div style={{ marginBottom: 20, fontSize: 13, color: 'var(--ag-text-secondary)' }}>
          Выберите два натальных профиля. Мы рассчитаем аспекты совместности и сгенерируем PDF-отчёт.
        </div>

        {natalProfiles.length < 2 ? (
          <div style={{ textAlign: 'center', padding: '16px 0', color: 'var(--ag-text-secondary)', fontSize: 13 }}>
            Для синастрии нужно минимум 2 натальных профиля.{' '}
            <a href="/dashboard/natal">Добавьте профиль</a>.
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: 'var(--ag-text-secondary)' }}>
                ЧЕЛОВЕК 1
              </div>
              <Select
                style={{ width: '100%' }}
                placeholder="Выберите профиль"
                options={profileOptions.filter((o) => o.value !== p2Id)}
                value={p1Id}
                onChange={setP1Id}
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: 'var(--ag-text-secondary)' }}>
                ЧЕЛОВЕК 2 (партнёр)
              </div>
              <Select
                style={{ width: '100%' }}
                placeholder="Выберите профиль"
                options={profileOptions.filter((o) => o.value !== p1Id)}
                value={p2Id}
                onChange={setP2Id}
              />
            </div>

            {/* Информационный блок */}
            <div style={{
              marginBottom: 16,
              padding: '10px 14px',
              background: 'var(--ag-bg-container)',
              border: '1px solid var(--ag-border)',
              borderRadius: 8,
              fontSize: 12,
              color: 'var(--ag-text-secondary)',
            }}>
              ℹ️ Генерация занимает 1–3 минуты. Когда отчёт будет готов — мы пришлём его на email.
            </div>
            {needsPayment && (
              <div style={{
                marginBottom: 16,
                padding: '10px 14px',
                background: 'rgba(201, 110, 140, 0.06)',
                border: '1px solid rgba(201, 110, 140, 0.3)',
                borderRadius: 8,
                fontSize: 12,
                color: 'var(--ag-text-secondary)',
              }}>
                💳 Бесплатные синастрии исчерпаны. Стоимость: <strong>{repeatPrice} ₽</strong>.
                Вы будете перенаправлены на страницу оплаты.
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button onClick={() => { setCreateOpen(false); setP1Id(null); setP2Id(null) }}>
                Отмена
              </Button>
              {needsPayment ? (
                <Button
                  type="primary"
                  icon={<HeartOutlined />}
                  disabled={!p1Id || !p2Id || p1Id === p2Id}
                  loading={purchaseMut.isPending}
                  onClick={() => purchaseMut.mutate()}
                  style={{ background: '#c96e8c', borderColor: '#c96e8c' }}
                >
                  Оплатить {repeatPrice} ₽ и создать
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<HeartOutlined />}
                  disabled={!p1Id || !p2Id || p1Id === p2Id}
                  loading={createMut.isPending}
                  onClick={() => createMut.mutate()}
                  style={{ background: '#c96e8c', borderColor: '#c96e8c' }}
                >
                  Создать синастрию
                </Button>
              )}
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}
