import { Typography } from 'antd'
import { useTranslation } from 'react-i18next'

const { Paragraph } = Typography

export function SupportPage() {
  const { t } = useTranslation()
  return (
    <div className="card">
      <div className="card-body">
        <Paragraph>{t('dashboard.supportIntro')}</Paragraph>
      </div>
    </div>
  )
}
