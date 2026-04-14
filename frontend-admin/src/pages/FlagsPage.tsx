import { useEffect, useState } from 'react'
import { Card, Switch, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchFlags, patchFlag } from '@/api/flags'
import type { FeatureFlagRow } from '@/types/admin'

export function FlagsPage() {
  const [rows, setRows] = useState<FeatureFlagRow[]>([])
  const load = () => void fetchFlags().then(setRows).catch(() => setRows([]))

  useEffect(() => {
    load()
  }, [])

  const columns: ColumnsType<FeatureFlagRow> = [
    { title: 'Ключ', dataIndex: 'key' },
    { title: 'Описание', dataIndex: 'description' },
    {
      title: 'Статус',
      dataIndex: 'enabled',
      render: (enabled: boolean) => <Tag color={enabled ? 'green' : 'default'}>{enabled ? 'enabled' : 'disabled'}</Tag>,
    },
    {
      title: 'Enabled',
      dataIndex: 'enabled',
      render: (enabled: boolean, row) => (
        <Switch checked={enabled} onChange={(v) => void patchFlag(row.key, v).then(load)} />
      ),
    },
  ]

  return (
    <>
      <div className="admin-page-title">Feature Flags</div>
      <Card>
        <Typography.Paragraph type="secondary">Изменения применяются сразу.</Typography.Paragraph>
        <Table rowKey="key" columns={columns} dataSource={rows} pagination={false} />
      </Card>
    </>
  )
}
