import { useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  AppstoreOutlined,
  CalendarOutlined,
  FileTextOutlined,
  MenuOutlined,
  QuestionCircleOutlined,
  SettingOutlined,
  ShoppingOutlined,
  StarOutlined,
} from '@ant-design/icons'
import { Grid } from 'antd'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/authStore'
import { useEffectiveThemeMode } from '@/hooks/useEffectiveThemeMode'
import { useThemeStore } from '@/stores/themeStore'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'
import { fetchMe } from '@/api/users'
import { fetchMySubscription } from '@/api/subscriptions'
import { listOrders } from '@/api/orders'
import '@/styles/cabinet-mockup.css'

const TITLE_KEYS: Record<string, string> = {
  '/dashboard': 'dashboard.navHome',
  '/dashboard/orders': 'dashboard.navOrders',
  '/dashboard/reports': 'dashboard.navReports',
  '/dashboard/natal': 'dashboard.navNatal',
  '/dashboard/subscription': 'dashboard.navSubscription',
  '/dashboard/settings': 'dashboard.navSettings',
  '/dashboard/support': 'dashboard.navSupport',
}

function LogoIcon() {
  return (
    <div className="sidebar-logo-icon">
      <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden>
        <circle cx="10" cy="10" r="8.5" stroke="white" strokeWidth="1" />
        <circle cx="10" cy="10" r="5" stroke="white" strokeWidth="0.8" opacity="0.6" />
        <circle cx="10" cy="1.5" r="2" fill="white" />
      </svg>
    </div>
  )
}

function initialsFromEmail(email: string | undefined): string {
  if (!email) return '?'
  const local = email.split('@')[0] ?? ''
  return (local.slice(0, 2) || '?').toUpperCase()
}

function displayNameFromEmail(email: string | undefined): string {
  if (!email) return '—'
  const local = email.split('@')[0] ?? ''
  const parts = local.split(/[._-]/).filter(Boolean)
  if (parts.length >= 2) {
    const first = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase()
    const last = parts[1].charAt(0).toUpperCase()
    return `${first} ${last}.`
  }
  return parts[0] ? parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase() : '—'
}

export function DashboardLayout() {
  const { t } = useTranslation()
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const screens = Grid.useBreakpoint()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const colorMode = useEffectiveThemeMode()
  const { isTwa } = useTwaEnvironment()
  const themeMode = useThemeStore((s) => s.mode)
  const setThemeMode = useThemeStore((s) => s.setMode)

  const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })
  const { data: subscription } = useQuery({ queryKey: ['subscription'], queryFn: fetchMySubscription })
  const { data: orders } = useQuery({ queryKey: ['orders'], queryFn: listOrders })

  const topTitle = useMemo(() => {
    const k = TITLE_KEYS[location.pathname]
    if (k) return t(k)
    return t('nav.dashboard')
  }, [location.pathname, t])

  const orderCount = orders?.length ?? 0
  const showProBadge = subscription?.status === 'active' && subscription.tariff_code?.toLowerCase().includes('pro')
  const planIsPro = subscription?.status === 'active' && showProBadge

  const navClass = ({ isActive }: { isActive: boolean }) => `nav-item cabinet-nav-link${isActive ? ' active' : ''}`

  const closeMobile = () => {
    if (!screens.md) setSidebarOpen(false)
  }

  const toggleTheme = () => {
    if (isTwa) return
    setThemeMode(themeMode === 'dark' ? 'light' : 'dark')
  }

  return (
    <div className="cabinet-mockup-root" data-theme={colorMode === 'dark' ? 'dark' : 'light'}>
      <div className="cabinet-layout">
        <aside className={`sidebar${sidebarOpen ? ' open' : ''}`} id="sidebar">
          <Link to="/dashboard" className="sidebar-logo" onClick={closeMobile} style={{ textDecoration: 'none', color: 'inherit' }}>
            <LogoIcon />
            Astrogen
          </Link>

          <nav className="sidebar-nav">
            <div className="nav-section-label">{t('dashboard.sectionCabinet')}</div>
            <NavLink to="/dashboard" end className={navClass} onClick={closeMobile}>
              <AppstoreOutlined />
              {t('dashboard.navHome')}
            </NavLink>
            <NavLink to="/dashboard/orders" className={navClass} onClick={closeMobile}>
              <ShoppingOutlined />
              {t('dashboard.navOrders')}
              {orderCount > 0 && <span className="nav-badge">{orderCount > 99 ? '99+' : orderCount}</span>}
            </NavLink>
            <NavLink to="/dashboard/reports" className={navClass} onClick={closeMobile}>
              <FileTextOutlined />
              {t('dashboard.navReports')}
            </NavLink>
            <NavLink to="/dashboard/natal" className={navClass} onClick={closeMobile}>
              <CalendarOutlined />
              {t('dashboard.navNatal')}
            </NavLink>

            <div className="nav-section-label">{t('dashboard.sectionAccount')}</div>
            <NavLink
              to="/dashboard/subscription"
              className={({ isActive }) => `${navClass({ isActive })}${isActive ? ' nav-sub-active' : ''}`}
              onClick={closeMobile}
            >
              <StarOutlined />
              {t('dashboard.navSubscription')}
              {showProBadge && (
                <span className="nav-badge" style={{ background: 'var(--purple-light)', color: 'var(--purple)' }}>
                  Pro
                </span>
              )}
            </NavLink>
            <NavLink to="/dashboard/settings" className={navClass} onClick={closeMobile}>
              <SettingOutlined />
              {t('dashboard.navSettings')}
            </NavLink>
            <NavLink to="/dashboard/support" className={navClass} onClick={closeMobile}>
              <QuestionCircleOutlined />
              {t('dashboard.navSupport')}
            </NavLink>
          </nav>

          <div className="sidebar-user">
            <div className="user-avatar">{initialsFromEmail(me?.email)}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="user-name">{displayNameFromEmail(me?.email)}</div>
              <div className={`user-plan${planIsPro ? ' user-plan--pro' : ''}`}>
                {subscription?.tariff_name ?? t('dashboard.planFree')}
              </div>
            </div>
            <button
              type="button"
              className="icon-btn"
              title={t('dashboard.logout')}
              onClick={() => {
                logout()
                window.location.assign('/')
              }}
              style={{ border: 'none', background: 'none', width: 28, height: 28 }}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
                <path
                  d="M9.5 4.5L12 7l-2.5 2.5M12 7H5.5M5.5 2H2.5A1 1 0 001.5 3v8a1 1 0 001 1h3"
                  stroke="currentColor"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </aside>

        <main className="cabinet-main">
          <div className="cabinet-topbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button
                type="button"
                className="icon-btn mobile-menu-btn"
                aria-label="Menu"
                onClick={() => setSidebarOpen((v) => !v)}
              >
                <MenuOutlined />
              </button>
              <div className="topbar-title">{topTitle}</div>
            </div>
            <div className="topbar-actions">
              <button
                type="button"
                className="icon-btn"
                title={t('dashboard.toggleTheme')}
                onClick={toggleTheme}
                disabled={isTwa}
              >
                {colorMode === 'dark' ? '☀' : '☽'}
              </button>
              <Link to="/order/tariff" className="btn btn-primary btn-sm">
                + {t('dashboard.newOrder')}
              </Link>
            </div>
          </div>

          <div className="cabinet-content">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
