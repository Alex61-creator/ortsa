import {
  Typography,
  Button,
  Row,
  Col,
  Card,
  Space,
  Carousel,
  Collapse,
  Flex,
  Tag,
} from 'antd'
import {
  RocketOutlined,
  CheckCircleOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons'
import { Helmet } from 'react-helmet-async'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { App } from 'antd'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { getOAuthAuthorizeUrl } from '@/api/auth'
import { listTariffs } from '@/api/tariffs'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'
import { useAuthStore } from '@/stores/authStore'

const { Title, Paragraph, Text } = Typography

const reviews = [
  {
    text: '«Очень подробный разбор! Узнала о себе много нового, особенно про влияние Сатурна. Спасибо!»',
    author: 'Анна, 32 года',
  },
  {
    text: '«Понравилось, что можно выбрать систему домов. Для меня это важно как для изучающего астрологию.»',
    author: 'Максим, 28 лет',
  },
  {
    text: '«Купил премиум, отчёт пришёл через 5 минут. Качество PDF на высоте, буду рекомендовать.»',
    author: 'Елена, 41 год',
  },
]

export function LandingPage() {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }
  const { isTwa } = useTwaEnvironment()
  const token = useAuthStore((s) => s.token)
  const { data: tariffs } = useQuery({ queryKey: ['tariffs'], queryFn: listTariffs })

  const miniAppLink = import.meta.env.VITE_TELEGRAM_MINIAPP_URL as string | undefined

  const oauth = (p: 'google' | 'yandex' | 'apple') => {
    window.location.href = getOAuthAuthorizeUrl(p)
  }

  const onTryFree = () => {
    if (token) navigate('/order/tariff')
    else message.info('Войдите через OAuth или Telegram, затем откройте заказ снова.')
  }

  const redirectNote = location.state?.from

  return (
    <>
      <Helmet>
        <title>AstroGen — персональная натальная карта и PDF‑отчёт</title>
        <meta
          name="description"
          content="Профессиональный астрологический разбор, ИИ‑интерпретация, оплата через ЮKassa, хранение отчётов в личном кабинете."
        />
        <meta property="og:title" content="AstroGen — натальная карта" />
        <meta
          property="og:description"
          content="Раскрой тайны своей судьбы с персональной натальной картой и PDF‑отчётом."
        />
      </Helmet>

      <section className="landing-hero">
        <div className="hero-glow" />
        <div className="starfield" />
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{ position: 'relative', zIndex: 1, maxWidth: 880 }}
        >
          <Title level={1} style={{ color: 'var(--ag-hero-text)', fontWeight: 700 }}>
            {t('landing.heroTitle')}
          </Title>
          <Paragraph style={{ fontSize: 18, color: 'var(--ag-hero-muted)' }}>
            {t('landing.heroSubtitle')}
          </Paragraph>
          {redirectNote && (
            <Paragraph type="warning">
              Чтобы открыть «{redirectNote}», войдите в аккаунт.
            </Paragraph>
          )}
          <Space wrap size="middle" style={{ marginTop: 24 }}>
            <Button type="primary" size="large" icon={<RocketOutlined />} onClick={onTryFree}>
              {t('landing.tryFree')}
            </Button>
            {!isTwa && miniAppLink && (
              <Button size="large" href={miniAppLink}>
                {t('landing.loginTelegram')}
              </Button>
            )}
          </Space>
          {!isTwa && (
            <div style={{ marginTop: 20 }}>
              <Text type="secondary">OAuth: </Text>
              <Space wrap>
                <Button onClick={() => oauth('google')}>{t('landing.loginGoogle')}</Button>
                <Button onClick={() => oauth('yandex')}>{t('landing.loginYandex')}</Button>
                <Button onClick={() => oauth('apple')}>{t('landing.loginApple')}</Button>
              </Space>
            </div>
          )}
          {isTwa && (
            <Paragraph type="secondary" style={{ marginTop: 16 }}>
              Вход выполняется автоматически через Telegram Mini App.
            </Paragraph>
          )}
        </motion.div>
      </section>

      <div className="landing-section">
        <Title level={2}>{t('landing.problemTitle')}</Title>
        <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
          <Col xs={24} md={12}>
            <Card title="Боль" bordered={false}>
              <Paragraph>
                <QuestionCircleOutlined /> Не понимаете, почему повторяются одни и те же жизненные
                сценарии.
              </Paragraph>
              <Paragraph>
                <QuestionCircleOutlined /> Хотите узнать свои сильные стороны и таланты.
              </Paragraph>
              <Paragraph>
                <QuestionCircleOutlined /> Ищете подходящее время для важных решений.
              </Paragraph>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Решение" bordered={false}>
              <Paragraph>
                <CheckCircleOutlined style={{ color: 'var(--ag-primary)' }} /> AstroGen — это не
                просто гороскоп. Мы строим вашу уникальную карту рождения и даём подробную
                интерпретацию от ИИ.
              </Paragraph>
              <Paragraph>
                <CheckCircleOutlined style={{ color: 'var(--ag-primary)' }} /> Вы получаете
                структурированный PDF‑отчёт с описанием планет в знаках, домах и аспектах.
              </Paragraph>
            </Card>
          </Col>
        </Row>
      </div>

      <div className="landing-section">
        <Title level={2}>{t('landing.howTitle')}</Title>
        <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
          {[
            {
              title: 'Введите данные',
              desc: 'Имя, дата, время и место рождения. Для продвинутых тарифов — система домов.',
            },
            {
              title: 'Выберите тариф и оплатите',
              desc: 'От бесплатного ознакомительного до премиум с транзитами на месяц.',
            },
            {
              title: 'Получите отчёт',
              desc: 'Через несколько минут PDF на почте и в личном кабинете.',
            },
          ].map((step, i) => (
            <Col xs={24} md={8} key={step.title}>
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
              >
                <Card>
                  <Tag color="blue">{i + 1}</Tag>
                  <Title level={4}>{step.title}</Title>
                  <Paragraph type="secondary">{step.desc}</Paragraph>
                </Card>
              </motion.div>
            </Col>
          ))}
        </Row>
      </div>

      <div className="landing-section" id="pricing">
        <Title level={2}>{t('landing.pricingTitle')}</Title>
        <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
          {(tariffs ?? []).map((tar) => (
            <Col xs={24} md={8} key={tar.code}>
              <Card hoverable title={tar.name}>
                <Title level={3} style={{ marginTop: 0 }}>
                  {tar.price} ₽
                </Title>
                <Paragraph type="secondary">Хранение: {tar.retention_days} дн.</Paragraph>
                <Button
                  type="primary"
                  block
                  style={{ marginTop: 12 }}
                  onClick={() => (token ? navigate('/order/tariff') : message.info('Сначала войдите в аккаунт'))}
                >
                  Выбрать тариф
                </Button>
              </Card>
            </Col>
          ))}
        </Row>
      </div>

      <div className="landing-section">
        <Title level={2}>{t('landing.previewTitle')}</Title>
        <Paragraph>
          Цветная натальная карта, таблицы аспектов, текстовая интерпретация по разделам.
        </Paragraph>
        <Flex gap="middle" wrap="wrap" justify="center" style={{ marginTop: 16 }}>
          {['#0e2a4a', '#153a5c', '#1a2332'].map((bg) => (
            <div
              key={bg}
              style={{
                width: 220,
                height: 300,
                borderRadius: 8,
                background: `linear-gradient(145deg, ${bg}, var(--ag-hero-edge))`,
                border: '1px solid var(--ag-preview-border)',
              }}
            />
          ))}
        </Flex>
      </div>

      <div className="landing-section">
        <Title level={2}>{t('landing.reviewsTitle')}</Title>
        <Carousel autoplay style={{ maxWidth: 640, margin: '24px auto' }}>
          {reviews.map((r) => (
            <div key={r.author} style={{ padding: 24 }}>
              <Card>
                <Paragraph>{r.text}</Paragraph>
                <Text strong>{r.author}</Text>
              </Card>
            </div>
          ))}
        </Carousel>
      </div>

      <div className="landing-section">
        <Title level={2}>{t('landing.faqTitle')}</Title>
        <Collapse
          style={{ marginTop: 24, maxWidth: 800 }}
          items={[
            {
              key: '1',
              label: 'Как быстро придёт отчёт?',
              children: (
                <Paragraph>
                  Обычно в течение 5–10 минут после оплаты. В редких случаях пиковой нагрузки — до
                  30 минут.
                </Paragraph>
              ),
            },
            {
              key: '2',
              label: 'Нужно ли знать точное время рождения?',
              children: (
                <Paragraph>
                  Желательно: от этого зависят дома и асцендент. Если время неизвестно, укажите 12:00 —
                  интерпретация будет менее точной.
                </Paragraph>
              ),
            },
            {
              key: '3',
              label: 'Как происходит оплата?',
              children: (
                <Paragraph>
                  Через ЮKassa: карты Visa, Mastercard, «Мир», электронные кошельки.
                </Paragraph>
              ),
            },
            {
              key: '4',
              label: 'Можно ли вернуть деньги?',
              children: (
                <Paragraph>
                  Да, в течение 14 дней, если отчёт ещё не был сгенерирован. Обратитесь в поддержку.
                </Paragraph>
              ),
            },
            {
              key: '5',
              label: 'Вы храните мои данные?',
              children: (
                <Paragraph>
                  Только с вашего согласия и в соответствии с 152‑ФЗ. Экспорт и удаление — в личном
                  кабинете.
                </Paragraph>
              ),
            },
          ]}
        />
      </div>

      <footer className="landing-section" style={{ paddingBottom: 48 }}>
        <Title level={4}>AstroGen</Title>
        <Paragraph type="secondary">
          Персональные натальные отчёты с ИИ‑интерпретацией и удобной оплатой.
        </Paragraph>
        {!isTwa && (
          <Space direction="vertical">
            <a href="/privacy-policy" onClick={(e) => e.preventDefault()}>
              Политика конфиденциальности
            </a>
            <a href="/offer" onClick={(e) => e.preventDefault()}>
              Публичная оферта
            </a>
            <a href="mailto:support@example.com">Поддержка</a>
          </Space>
        )}
        {isTwa && (
          <Paragraph type="secondary">
            Юридические документы доступны на сайте сервиса в браузере.
          </Paragraph>
        )}
        <div style={{ marginTop: 24 }}>
          <Button type="primary" size="large" onClick={onTryFree}>
            {t('landing.footerCta')}
          </Button>
        </div>
        <Paragraph type="secondary" style={{ marginTop: 24 }}>
          {t('landing.copyright', { year: 2026 })}
        </Paragraph>
      </footer>
    </>
  )
}
