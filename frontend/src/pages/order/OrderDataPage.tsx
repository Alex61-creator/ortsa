import {
  Typography,
  Button,
  Form,
  Input,
  Select,
  DatePicker,
  TimePicker,
  Checkbox,
  InputNumber,
  Space,
  Modal,
  List,
  Steps,
  App,
} from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createNatalData } from '@/api/natal'
import { fetchMe } from '@/api/users'
import { nominatimSearch, type GeocodeHit } from '@/lib/geocoder'
import { getSelectableTimezones } from '@/lib/timezones'
import { HOUSE_SYSTEMS, canChooseHouseSystem } from '@/lib/tariff'
import { useOrderWizardStore } from '@/stores/orderWizardStore'
import { useEffect, useState } from 'react'

const { Title } = Typography

const schema = z.object({
  full_name: z.string().min(1).max(80),
  birth_date: z.custom<Dayjs | null>((v) => v !== null && dayjs.isDayjs(v), 'Дата'),
  birth_time: z.custom<Dayjs | null>((v) => v !== null && dayjs.isDayjs(v), 'Время'),
  birth_place: z.string().min(1).max(120),
  lat: z.number(),
  lon: z.number(),
  timezone: z.string().min(1),
  house_system: z.string(),
  accept_privacy_policy: z.boolean(),
})

type FormValues = z.infer<typeof schema>

export function OrderDataPage() {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const tariffCode = useOrderWizardStore((s) => s.tariffCode)
  const setNatalId = useOrderWizardStore((s) => s.setNatalDataId)
  const [geoHits, setGeoHits] = useState<GeocodeHit[]>([])
  const [geoOpen, setGeoOpen] = useState(false)

  const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: '',
      birth_place: '',
      lat: 55.7558,
      lon: 37.6173,
      timezone: 'Europe/Moscow',
      house_system: 'P',
      accept_privacy_policy: Boolean(me?.consent_given_at),
      birth_date: dayjs(),
      birth_time: dayjs().hour(12).minute(0).second(0),
    },
  })

  useEffect(() => {
    if (me?.consent_given_at) {
      form.setValue('accept_privacy_policy', true)
    }
  }, [me, form])

  const save = useMutation({
    mutationFn: async (values: FormValues) => {
      if (!me?.consent_given_at && !values.accept_privacy_policy) {
        message.error(t('natal.privacyConsent'))
        throw new Error('consent')
      }
      const d = values.birth_date!
      const tm = values.birth_time!
      const birth_date = d.startOf('day').format('YYYY-MM-DDTHH:mm:ss')
      const birth_time = d.hour(tm.hour()).minute(tm.minute()).second(tm.second()).format('YYYY-MM-DDTHH:mm:ss')
      const hs = canChooseHouseSystem(tariffCode) ? values.house_system : 'P'
      return createNatalData({
        full_name: values.full_name,
        birth_date,
        birth_time,
        birth_place: values.birth_place,
        lat: values.lat,
        lon: values.lon,
        timezone: values.timezone,
        house_system: hs,
        accept_privacy_policy: values.accept_privacy_policy || Boolean(me?.consent_given_at),
      })
    },
    onSuccess: (natal) => {
      void qc.invalidateQueries({ queryKey: ['natal-data'] })
      void qc.invalidateQueries({ queryKey: ['me'] })
      setNatalId(natal.id)
      navigate('/order/confirm')
    },
  })

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

  if (!tariffCode) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={4}>{t('order.fallbackSelectTariff')}</Title>
        <Button type="primary" onClick={() => navigate('/order/tariff')}>
          {t('order.fallbackToTariffs')}
        </Button>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 560, margin: '0 auto', padding: 24 }}>
      <Steps
        current={1}
        items={[
          { title: t('order.stepTariff') },
          { title: t('order.stepData') },
          { title: t('order.stepConfirm') },
        ]}
        style={{ marginBottom: 32 }}
      />
      <Title level={2}>{t('order.dataTitle')}</Title>
      <Form layout="vertical">
        <Form.Item label={t('natal.labelFullName')} required>
          <Controller name="full_name" control={form.control} render={({ field }) => <Input {...field} />} />
        </Form.Item>
        <Form.Item label={t('natal.labelBirthDate')} required>
          <Controller name="birth_date" control={form.control} render={({ field }) => <DatePicker style={{ width: '100%' }} {...field} />} />
        </Form.Item>
        <Form.Item label={t('natal.labelBirthTime')} required>
          <Controller
            name="birth_time"
            control={form.control}
            render={({ field }) => <TimePicker style={{ width: '100%' }} format="HH:mm" {...field} />}
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
        {!me?.consent_given_at && (
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
        <Button type="primary" loading={save.isPending} onClick={() => void form.handleSubmit((v) => save.mutate(v))()}>
          {t('common.continue')}
        </Button>
      </Form>

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
