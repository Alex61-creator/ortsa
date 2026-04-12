import { Typography, Card, Switch, Button, Space, Modal } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { deleteAccount, exportUserData, fetchMe, patchMeConsent } from '@/api/users'
import { useAuthStore } from '@/stores/authStore'

const { Title, Paragraph } = Typography

export function ProfilePage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const logout = useAuthStore((s) => s.logout)

  const { data: me, isLoading } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

  const patchConsent = useMutation({
    mutationFn: (v: boolean) => patchMeConsent(v),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['me'] }),
  })

  const onExport = async () => {
    const blob = await exportUserData()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'user_data_export.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const onDelete = () => {
    Modal.confirm({
      title: t('profile.deleteConfirm'),
      okType: 'danger',
      onOk: async () => {
        await deleteAccount()
        logout()
        window.location.href = '/'
      },
    })
  }

  if (isLoading || !me) return null

  const hasConsent = Boolean(me.consent_given_at)

  return (
    <div>
      <Title level={2}>{t('profile.title')}</Title>
      <Card style={{ maxWidth: 560 }}>
        <Paragraph>
          <strong>{t('profile.email')}:</strong> {me.email}
        </Paragraph>
        <Paragraph>
          <Space>
            <span>{t('profile.consent')}</span>
            <Switch
              checked={hasConsent}
              disabled={hasConsent}
              loading={patchConsent.isPending}
              onChange={(v) => {
                if (v) patchConsent.mutate(true)
              }}
            />
          </Space>
        </Paragraph>
        <Space direction="vertical" style={{ marginTop: 16 }}>
          <Button onClick={() => void onExport()}>{t('profile.export')}</Button>
          <Button danger onClick={onDelete}>
            {t('profile.deleteAccount')}
          </Button>
        </Space>
      </Card>
    </div>
  )
}
