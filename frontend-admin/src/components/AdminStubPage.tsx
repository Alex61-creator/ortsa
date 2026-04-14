import { Card, Typography } from 'antd'

interface Props {
  title: string
  description: string
}

export function AdminStubPage({ title, description }: Props) {
  return (
    <>
      <div className="admin-page-title">{title}</div>
      <Card>
        <Typography.Paragraph>{description}</Typography.Paragraph>
      </Card>
    </>
  )
}
