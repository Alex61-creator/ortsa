import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Button,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  TimePicker,
  Checkbox,
  InputNumber,
  Space,
  List,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import 'dayjs/locale/ru'
import 'dayjs/locale/en'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'
import { createNatalData, deleteNatalData, listNatalData, updateNatalData } from '@/api/natal'
import type { NatalDataOut } from '@/types/api'
import { nominatimSearch, type GeocodeHit } from '@/lib/geocoder'
import { getSelectableTimezones } from '@/lib/timezones'
import { HOUSE_SYSTEMS, canChooseHouseSystem } from '@/lib/tariff'
import { useOrderWizardStore } from '@/stores/orderWizardStore'

const schema = z.object({
  full_name: z.string().min(1).max(80),
  birth_date: z.custom<Dayjs | null>((v) => v === null || dayjs.isDayjs(v), 'Дата'),
  birth_time: z.custom<Dayjs | null>((v) => v === null || dayjs.isDayjs(v), 'Время'),
  birth_place: z.string().min(1).max(120),
  lat: z.number().min(-90).max(90),
  lon: z.number().min(-180).max(180),
  timezone: z.string().min(1),
  house_system: z.string().min(1),
  accept_privacy_policy: z.boolean(),
})

type FormValues = z.infer<typeof schema>

function DateIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden>
      <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1" />
      <line x1="6.5" y1="4" x2="6.5" y2="7" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="6.5" cy="9" r="0.6" fill="currentColor" />
    </svg>
  )
}

function PlaceIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden>
      <circle cx="6.5" cy="5.5" r="2.5" stroke="currentColor" strokeWidth="1" />
      <path d="M2 11.5c0-2.49 2.01-4.5 4.5-4.5s4.5 2.01 4.5 4.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden>
      <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1" />
      <path d="M6.5 3.5v3.5l2 1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

export function NatalDataPage() {
  const { t, i18n } = useTranslation()
  const qc = useQueryClient()
  const tariffCode = useOrderWizardStore((s) => s.tariffCode)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<NatalDataOut | null>(null)
  const [geoHits, setGeoHits] = useState<GeocodeHit[]>([])
  const [geoOpen, setGeoOpen] = useState(false)

  const locale = i18n.language?.startsWith('en') ? 'en' : 'ru'

  const { data, isLoading } = useQuery({ queryKey: ['natal-data'], queryFn: listNatalData })

  const sorted = useMemo(() => [...(data ?? [])].sort((a, b) => a.id - b.id), [data])
  const primaryId = sorted[0]?.id

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: '',
      birth_place: '',
      lat: 55.7558,
      lon: 37.6173,
      timezone: 'Europe/Moscow',
      house_system: 'P',
      accept_privacy_policy: false,
      birth_date: dayjs(),
      birth_time: dayjs().hour(12).minute(0).second(0),
    },
  })

  const save = useMutation({
    mutationFn: async (values: FormValues) => {
      if (!values.birth_date || !values.birth_time) throw new Error('date')
      const d = values.birth_date
      const tm = values.birth_time
      const birth_date = d.startOf('day').format('YYYY-MM-DDTHH:mm:ss')
      const birth_time = d.hour(tm.hour()).minute(tm.minute()).second(tm.second()).format('YYYY-MM-DDTHH:mm:ss')
      const hs = canChooseHouseSystem(tariffCode) ? values.house_system : 'P'
      if (editing) {
        return updateNatalData(editing.id, {
          full_name: values.full_name,
          birth_place: values.birth_place,
          lat: values.lat,
          lon: values.lon,
          timezone: values.timezone,
          house_system: hs,
        })
      }
      return createNatalData({
        full_name: values.full_name,
        birth_date,
        birth_time,
        birth_place: values.birth_place,
        lat: values.lat,
        lon: values.lon,
        timezone: values.timezone,
        house_system: hs,
        accept_privacy_policy: values.accept_privacy_policy,
      })
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['natal-data'] })
      void qc.invalidateQueries({ queryKey: ['me'] })
      setOpen(false)
      setEditing(null)
      form.reset()
    },
  })

  const remove = useMutation({
    mutationFn: (id: number) => deleteNatalData(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['natal-data'] }),
  })

  const openCreate = () => {
    setEditing(null)
    form.reset({
      full_name: '',
      birth_place: '',
      lat: 55.7558,
      lon: 37.6173,
      timezone: 'Europe/Moscow',
      house_system: 'P',
      birth_date: dayjs(),
      birth_time: dayjs().hour(12).minute(0).second(0),
      accept_privacy_policy: false,
    })
    setOpen(true)
  }

  const openEdit = (row: NatalDataOut) => {
    setEditing(row)
    form.reset({
      full_name: row.full_name,
      birth_place: row.birth_place,
      lat: row.lat,
      lon: row.lon,
      timezone: row.timezone,
      house_system: row.house_system,
      birth_date: dayjs(row.birth_date),
      birth_time: dayjs(row.birth_time),
      accept_privacy_policy: true,
    })
    setOpen(true)
  }

  const confirmDelete = (row: NatalDataOut) => {
    Modal.confirm({
      title: t('natal.deleteConfirmTitle'),
      content: t('natal.deleteConfirmBody'),
      okText: t('common.delete'),
      cancelText: t('common.cancel'),
      okButtonProps: { danger: true },
      onOk: () => remove.mutateAsync(row.id),
    })
  }

  const searchGeo = async () => {
    const q = form.getValues('birth_place')
    const hits = await nominatimSearch(q)
    setGeoHits(hits)
    setGeoOpen(true)
  }

  const pickHit = (h: GeocodeHit) => {
    form.setValue('birth_place', h.display_name)
    form.setValue('lat', parseFloat(h.lat))
    form.setValue('lon', parseFloat(h.lon))
    setGeoOpen(false)
  }

  const formatBirthDate = (row: NatalDataOut) =>
    dayjs(row.birth_date)
      .locale(locale)
      .format(locale === 'ru' ? 'D MMMM YYYY' : 'MMMM D, YYYY')

  const formatTime = (row: NatalDataOut) => {
    const tm = dayjs(row.birth_time).format('HH:mm')
    const tzShort = row.timezone.includes('/') ? row.timezone.split('/').slice(-2).join('/') : row.timezone
    return `${tm} (${tzShort})`
  }

  return (
    <div>
      <div style={{ marginBottom: 16, fontSize: 14, color: 'var(--text-2)' }}>{t('natal.intro')}</div>

      <div className="natal-grid">
        {sorted.map((row) => {
          const isPrimary = row.id === primaryId
          return (
            <div
              key={row.id}
              className={`natal-card${isPrimary ? ' active-card' : ''}`}
              style={{ cursor: 'default' }}
            >
              <div className="natal-card-name">
                {row.full_name}
                {isPrimary && (
                  <span className="tag tag-blue" style={{ fontSize: 11 }}>
                    {t('natal.badgeMe')}
                  </span>
                )}
              </div>
              <div className="natal-card-row">
                <DateIcon />
                {formatBirthDate(row)}
              </div>
              <div className="natal-card-row">
                <PlaceIcon />
                {row.birth_place}
              </div>
              <div className="natal-card-row">
                <ClockIcon />
                {formatTime(row)}
              </div>
              <div className="natal-card-actions">
                <button type="button" className="btn btn-default btn-sm" onClick={() => openEdit(row)}>
                  {t('common.edit')}
                </button>
                {isPrimary ? (
                  <Link to="/dashboard/reports" className="btn btn-ghost btn-sm" style={{ textDecoration: 'none' }}>
                    {t('natal.reports')}
                  </Link>
                ) : (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    style={{ color: 'var(--danger)' }}
                    onClick={() => confirmDelete(row)}
                  >
                    {t('common.delete')}
                  </button>
                )}
              </div>
            </div>
          )
        })}

        <button
          type="button"
          className="add-natal-card"
          onClick={openCreate}
          disabled={isLoading}
          style={{ border: 'none', font: 'inherit' }}
        >
          <PlusOutlined style={{ fontSize: 28, color: 'inherit' }} />
          <div style={{ fontSize: 14, fontWeight: 500 }}>{t('natal.addCard')}</div>
          <div style={{ fontSize: 12 }}>{t('natal.addCardHint')}</div>
        </button>
      </div>

      <Modal
        title={editing ? t('natal.modalEdit') : t('natal.modalNew')}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => void form.handleSubmit((v) => save.mutate(v))()}
        confirmLoading={save.isPending}
        width={560}
      >
        <Form layout="vertical">
          <Form.Item label={t('natal.labelFullName')} required>
            <Controller name="full_name" control={form.control} render={({ field }) => <Input {...field} />} />
          </Form.Item>
          <Form.Item label={t('natal.labelBirthDate')} required={!editing}>
            <Controller
              name="birth_date"
              control={form.control}
              render={({ field }) => (
                <DatePicker style={{ width: '100%' }} disabled={Boolean(editing)} {...field} />
              )}
            />
          </Form.Item>
          <Form.Item label={t('natal.labelBirthTime')} required={!editing}>
            <Controller
              name="birth_time"
              control={form.control}
              render={({ field }) => (
                <TimePicker style={{ width: '100%' }} format="HH:mm" disabled={Boolean(editing)} {...field} />
              )}
            />
          </Form.Item>
          <Form.Item label={t('natal.labelPlace')} required>
            <Space.Compact style={{ width: '100%' }}>
              <Controller name="birth_place" control={form.control} render={({ field }) => <Input {...field} />} />
              <Button type="default" onClick={() => void searchGeo()}>
                {t('natal.searchPlace')}
              </Button>
            </Space.Compact>
          </Form.Item>
          <Space wrap>
            <Form.Item label={t('natal.labelLat')}>
              <Controller
                name="lat"
                control={form.control}
                render={({ field }) => <InputNumber step={0.0001} style={{ width: 160 }} {...field} />}
              />
            </Form.Item>
            <Form.Item label={t('natal.labelLon')}>
              <Controller
                name="lon"
                control={form.control}
                render={({ field }) => <InputNumber step={0.0001} style={{ width: 160 }} {...field} />}
              />
            </Form.Item>
          </Space>
          <Form.Item label={t('natal.labelTz')}>
            <Controller
              name="timezone"
              control={form.control}
              render={({ field }) => (
                <Select
                  showSearch
                  optionFilterProp="label"
                  style={{ width: '100%' }}
                  options={getSelectableTimezones().map((z) => ({ label: z, value: z }))}
                  {...field}
                />
              )}
            />
          </Form.Item>
          {canChooseHouseSystem(tariffCode) && (
            <Form.Item label={t('natal.labelHouse')}>
              <Controller
                name="house_system"
                control={form.control}
                render={({ field }) => (
                  <Select
                    style={{ width: '100%' }}
                    options={HOUSE_SYSTEMS.map((h) => ({ label: h.label, value: h.value }))}
                    {...field}
                  />
                )}
              />
            </Form.Item>
          )}
          {!editing && (
            <Form.Item>
              <Controller
                name="accept_privacy_policy"
                control={form.control}
                render={({ field }) => (
                  <Checkbox checked={field.value} onChange={(e) => field.onChange(e.target.checked)}>
                    {t('natal.privacyConsent')}
                  </Checkbox>
                )}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal title={t('natal.pickPlaceTitle')} open={geoOpen} footer={null} onCancel={() => setGeoOpen(false)}>
        <List
          dataSource={geoHits}
          renderItem={(item) => (
            <List.Item>
              <Button type="link" onClick={() => pickHit(item)}>
                {item.display_name}
              </Button>
            </List.Item>
          )}
        />
      </Modal>
    </div>
  )
}
