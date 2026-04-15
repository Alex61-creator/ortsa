import { useState } from 'react'
import { App, Button, Modal, Select, Spin, Tag, Tooltip } from 'antd'
import {
  DeleteOutlined,
  DownloadOutlined,
  HeartOutlined,
  PlusOutlined,
  ReloadOutlined,
  SyncOutlined,
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

function regenAvailableIn(s: SynastryOut): string | null {
  if (!s.next_regen_allowed_at) return null
  const at = dayjs(s.next_regen_allowed_at)
  if (at.isBefore(dayjs())) return null
  return at.fromNow(true)
}

// ── Main Page ─────────────────────────────────────────────────────────────────

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
      // Polling while any report is pending/processing
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
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail ?? 'Не удалось создать синастрию')
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
      content: `«${names}» будет удалена. Слот квоты освободится.`,
      okText: 'Удалить',
      okButtonProps: { danger: true },
      onOk: () => deleteMut.mutate(id),
    })
  }

  // ── Quota display ──────────────────────────────────────────────────────────
  const canCreate = quota?.has_access && (quota.pairs_used < quota.pairs_max)
  const profileOptions = natalProfiles.map((nd) => ({
    value: nd.id,
    label: `${nd.full_name} · ${nd.birth_place}`,
  }))

  if (quotaLoading) {
    return (
      <div style={{ padding: 32, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  // No access
  if (!quota?.has_access) {
    return (
      <div style={{ padding: 24 }}>
        <div className="synastry-locked-banner">
          <HeartOutlined style={{ fontSize: 32, color: 'var(--ag-primary)', marginBottom: 12 }} />
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Синастрия недоступна</div>
          <div style={{ fontSize: 13, color: 'var(--ag-text-secondary)', marginBottom: 16, maxWidth: 420 }}>
            Анализ совместности двух натальных карт доступен на тарифах{' '}
            <strong>Набор 3</strong>, <strong>Astro Pro (месяц)</strong> и{' '}
            <strong>Astro Pro (год)</strong>.
          </div>
          <Button type="primary" href="/order/tariff">
            Выбрать тариф
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 2 }}>
            <HeartOutlined style={{ marginRight: 8, color: '#c96e8c' }} />
            Синастрия
          </div>
          <div style={{ fontSize: 12, color: 'var(--ag-text-secondary)' }}>
            Использовано {quota.pairs_used} из {quota.pairs_max} пар
            {quota.pairs_used > 0 && (
              <span style={{ marginLeft: 8, color: 'var(--ag-text-secondary)' }}>
                · Удалите пару, чтобы добавить новую
              </span>
            )}
          </div>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          disabled={!canCreate}
          onClick={() => setCreateOpen(true)}
        >
          Новая синастрия
        </Button>
      </div>

      {/* ── List ── */}
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
            <Button type="primary" icon={<PlusOutlined />} style={{ marginTop: 16 }} onClick={() => setCreateOpen(true)}>
              Создать синастрию
            </Button>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {list.map((s) => {
            const waitTime = regenAvailableIn(s)
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
                      waitTime
                        ? `Следующая регенерация через ${waitTime}`
                        : 'Перегенерировать с актуальными данными'
                    }
                  >
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      loading={regenMut.isPending && regenMut.variables === s.id}
                      disabled={
                        s.status === 'processing' ||
                        s.status === 'pending' ||
                        !!waitTime
                      }
                      onClick={() => regenMut.mutate(s.id)}
                    >
                      {waitTime ? `Доступно через ${waitTime}` : 'Перегенерировать'}
                    </Button>
                  </Tooltip>

                  {/* Delete */}
                  <Tooltip title="Удалить синастрию (освобождает слот)">
                    <Button
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      loading={deleteMut.isPending && deleteMut.variables === s.id}
                      onClick={() => confirmDelete(s.id, pairName)}
                    />
                  </Tooltip>
                </div>

                {/* Abuse hint — данные не изменились */}
                {s.pdf_ready && (
                  <div style={{ fontSize: 11, color: 'var(--ag-text-secondary)', marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--ag-border)' }}>
                    💡 Чтобы получить обновлённый отчёт — отредактируйте дату, время или место рождения одного из партнёров в разделе{' '}
                    <a href="/dashboard/natal">«Натальные данные»</a>,{' '}
                    затем нажмите «Перегенерировать».
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── Create modal ── */}
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
        width={460}
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
            <div style={{ marginBottom: 16, padding: '8px 12px', background: 'var(--ag-bg-container)', border: '1px solid var(--ag-border)', borderRadius: 8, fontSize: 12, color: 'var(--ag-text-secondary)' }}>
              ℹ️ Генерация занимает 1–3 минуты. Когда отчёт будет готов — мы пришлём его на email.
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button onClick={() => { setCreateOpen(false); setP1Id(null); setP2Id(null) }}>
                Отмена
              </Button>
              <Button
                type="primary"
                icon={<HeartOutlined />}
                disabled={!p1Id || !p2Id || p1Id === p2Id}
                loading={createMut.isPending}
                onClick={() => createMut.mutate()}
              >
                Создать синастрию
              </Button>
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}
