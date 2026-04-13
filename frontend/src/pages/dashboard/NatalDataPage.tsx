import { useState } from 'react'
import {
  Table,
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

export function NatalDataPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const tariffCode = useOrderWizardStore((s) => s.tariffCode)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<NatalDataOut | null>(null)
  const [geoHits, setGeoHits] = useState<GeocodeHit[]>([])
  const [geoOpen, setGeoOpen] = useState(false)

  const { data, isLoading } = useQuery({ queryKey: ['natal-data'], queryFn: listNatalData })

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
      if (!values.birth_date || !values.birth_time) throw new Error('Дата и время обязательны')
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

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Добавить
        </Button>
      </div>
      <Table<NatalDataOut>
        loading={isLoading}
        rowKey="id"
        dataSource={data ?? []}
        columns={[
          { title: 'Имя', dataIndex: 'full_name' },
          { title: 'Место', dataIndex: 'birth_place' },
          { title: 'Дата', render: (_, r) => dayjs(r.birth_date).format('YYYY-MM-DD') },
          {
            title: '',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>
                  {t('common.edit')}
                </Button>
                <Button size="small" danger onClick={() => remove.mutate(row.id)}>
                  {t('common.delete')}
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={editing ? 'Редактировать' : 'Новые данные'}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => void form.handleSubmit((v) => save.mutate(v))()}
        confirmLoading={save.isPending}
        width={560}
      >
        <Form layout="vertical">
          <Form.Item label="ФИО" required>
            <Controller name="full_name" control={form.control} render={({ field }) => <Input {...field} />} />
          </Form.Item>
          <Form.Item label="Дата рождения" required={!editing}>
            <Controller
              name="birth_date"
              control={form.control}
              render={({ field }) => (
                <DatePicker style={{ width: '100%' }} disabled={Boolean(editing)} {...field} />
              )}
            />
          </Form.Item>
          <Form.Item label="Время рождения" required={!editing}>
            <Controller
              name="birth_time"
              control={form.control}
              render={({ field }) => (
                <TimePicker style={{ width: '100%' }} format="HH:mm" disabled={Boolean(editing)} {...field} />
              )}
            />
          </Form.Item>
          <Form.Item label="Место" required>
            <Space.Compact style={{ width: '100%' }}>
              <Controller name="birth_place" control={form.control} render={({ field }) => <Input {...field} />} />
              <Button type="default" onClick={() => void searchGeo()}>
                Найти
              </Button>
            </Space.Compact>
          </Form.Item>
          <Space wrap>
            <Form.Item label="Широта">
              <Controller
                name="lat"
                control={form.control}
                render={({ field }) => <InputNumber step={0.0001} style={{ width: 160 }} {...field} />}
              />
            </Form.Item>
            <Form.Item label="Долгота">
              <Controller
                name="lon"
                control={form.control}
                render={({ field }) => <InputNumber step={0.0001} style={{ width: 160 }} {...field} />}
              />
            </Form.Item>
          </Space>
          <Form.Item label="Часовой пояс">
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
            <Form.Item label="Система домов">
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
                    Согласие с политикой обработки ПДн
                  </Checkbox>
                )}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal title="Выберите место" open={geoOpen} footer={null} onCancel={() => setGeoOpen(false)}>
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
