import { useEffect, useState } from 'react'
import { Button, Card, Space, Switch, Table, Tag, Typography, message } from 'antd'
import { ArrowDownOutlined, ArrowUpOutlined, ReloadOutlined } from '@ant-design/icons'
import { fetchLlmProviders, toggleLlmProvider, setLlmFallbackOrder } from '@/api/settings'
import type { LlmProviderConfig } from '@/types/admin'
import { extractApiErrorMessage } from '@/utils/apiError'

const { Title, Text } = Typography

const PROVIDER_LABELS: Record<string, string> = {
  claude: 'Claude Sonnet 4.6',
  grok: 'Grok 4.20',
  deepseek: 'DeepSeek Chat',
}

const PROVIDER_COLORS: Record<string, string> = {
  claude: 'purple',
  grok: 'blue',
  deepseek: 'green',
}

export function LlmSettingsPage() {
  const [providers, setProviders] = useState<LlmProviderConfig[]>([])
  const [fallbackOrder, setFallbackOrder] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<string | null>(null)
  const [orderSaving, setOrderSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const data = await fetchLlmProviders()
      setProviders(data.providers.sort((a, b) => a.order_index - b.order_index))
      setFallbackOrder(data.fallback_order)
    } catch (e) {
      message.error(extractApiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleToggle = async (provider: string, enabled: boolean) => {
    setSaving(provider)
    try {
      await toggleLlmProvider(provider, enabled)
      setProviders(prev => prev.map(p => p.provider === provider ? { ...p, enabled } : p))
      message.success(`${PROVIDER_LABELS[provider] ?? provider} ${enabled ? 'включён' : 'отключён'}`)
    } catch (e) {
      message.error(extractApiErrorMessage(e))
    } finally {
      setSaving(null)
    }
  }

  const moveProvider = (index: number, direction: -1 | 1) => {
    const newOrder = [...fallbackOrder]
    const swapIndex = index + direction
    if (swapIndex < 0 || swapIndex >= newOrder.length) return
    ;[newOrder[index], newOrder[swapIndex]] = [newOrder[swapIndex], newOrder[index]]
    setFallbackOrder(newOrder)
  }

  const saveOrder = async () => {
    setOrderSaving(true)
    try {
      await setLlmFallbackOrder(fallbackOrder)
      message.success('Порядок failover сохранён')
      await load()
    } catch (e) {
      message.error(extractApiErrorMessage(e))
    } finally {
      setOrderSaving(false)
    }
  }

  const columns = [
    {
      title: 'Провайдер',
      dataIndex: 'provider',
      render: (v: string) => (
        <Space>
          <Tag color={PROVIDER_COLORS[v] ?? 'default'}>{PROVIDER_LABELS[v] ?? v}</Tag>
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'enabled',
      render: (enabled: boolean, row: LlmProviderConfig) => (
        <Switch
          checked={enabled}
          loading={saving === row.provider}
          onChange={(val) => handleToggle(row.provider, val)}
          checkedChildren="Вкл"
          unCheckedChildren="Выкл"
        />
      ),
    },
    {
      title: 'Позиция в fallback',
      dataIndex: 'order_index',
      render: (_: number, row: LlmProviderConfig) => {
        const idx = fallbackOrder.indexOf(row.provider)
        return (
          <Space>
            <Text type="secondary">#{idx + 1}</Text>
            <Button
              size="small"
              icon={<ArrowUpOutlined />}
              disabled={idx <= 0}
              onClick={() => moveProvider(idx, -1)}
            />
            <Button
              size="small"
              icon={<ArrowDownOutlined />}
              disabled={idx >= fallbackOrder.length - 1}
              onClick={() => moveProvider(idx, 1)}
            />
          </Space>
        )
      },
    },
  ]

  // Sort table by current fallback order
  const sortedProviders = [...providers].sort((a, b) => {
    const ia = fallbackOrder.indexOf(a.provider)
    const ib = fallbackOrder.indexOf(b.provider)
    return ia - ib
  })

  return (
    <div style={{ maxWidth: 800 }}>
      <Title level={3}>LLM Настройки</Title>
      <Text type="secondary">
        Управление провайдерами: включение/отключение и порядок failover-цепочки.
        Изменения применяются в течение 60 секунд (Redis TTL).
      </Text>

      <Card
        style={{ marginTop: 24 }}
        title="Провайдеры и порядок failover"
        extra={
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            Обновить
          </Button>
        }
      >
        <Table
          dataSource={sortedProviders}
          columns={columns}
          rowKey="provider"
          loading={loading}
          pagination={false}
          size="middle"
        />

        <div style={{ marginTop: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
          <Text type="secondary">
            Текущий порядок:{' '}
            {fallbackOrder.map((p, i) => (
              <span key={p}>
                {i > 0 && ' → '}
                <Tag color={PROVIDER_COLORS[p] ?? 'default'}>{PROVIDER_LABELS[p] ?? p}</Tag>
              </span>
            ))}
          </Text>
          <Button
            type="primary"
            onClick={saveOrder}
            loading={orderSaving}
            disabled={orderSaving}
          >
            Сохранить порядок
          </Button>
        </div>
      </Card>

      <Card style={{ marginTop: 16 }} title="Справка">
        <Space direction="vertical" size="small">
          <Text>
            <strong>Claude Sonnet 4.6</strong> — основной провайдер. Поддерживает кеширование системного
            промпта (эфемерный кеш Anthropic, экономия ~90% на input-токенах при повторных запросах).
          </Text>
          <Text>
            <strong>Grok 4.20</strong> — OpenAI-совместимый API xAI. Включается как резерв.
          </Text>
          <Text>
            <strong>DeepSeek Chat</strong> — самый дешёвый вариант. Рекомендуется как последний fallback.
          </Text>
          <Text type="secondary">
            При отказе провайдера (сетевая ошибка) circuit breaker блокирует его на 5 минут после 10 сбоев.
            Запросы автоматически переходят к следующему в цепочке.
          </Text>
        </Space>
      </Card>
    </div>
  )
}
