import type { ThemeConfig } from 'antd'
import { theme as antdTheme } from 'antd'

/** Ant Design primary (как в UI Kit). */
export const COLOR_PRIMARY = '#1677FF'
export const COLOR_ERROR = '#FF4D4F'
export const COLOR_PRIMARY_BG = '#E6F4FF'

/** Светлая тема: фон страницы и контейнеры (как на референсе). */
export const LIGHT = {
  layout: '#F5F5F5',
  container: '#FFFFFF',
  text: 'rgba(0, 0, 0, 0.88)',
  textSecondary: '#595959',
  border: '#D9D9D9',
} as const

/** Тёмная тема: фоны в духе Ant Design Dark. */
export const DARK = {
  layout: '#141414',
  elevated: '#1F1F1F',
  text: 'rgba(255, 255, 255, 0.85)',
} as const

export function getAntdTheme(mode: 'dark' | 'light'): ThemeConfig {
  const isDark = mode === 'dark'
  return {
    algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: COLOR_PRIMARY,
      colorError: COLOR_ERROR,
      colorInfo: COLOR_PRIMARY,
      fontFamily:
        '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      borderRadius: 6,
      ...(isDark
        ? {
            colorBgBase: DARK.layout,
          }
        : {
            colorBgLayout: LIGHT.layout,
            colorBgContainer: LIGHT.container,
            colorText: LIGHT.text,
            colorTextSecondary: LIGHT.textSecondary,
            colorTextTertiary: '#BFBFBF',
            colorBorder: LIGHT.border,
            colorBorderSecondary: '#F0F0F0',
            colorInfoBg: COLOR_PRIMARY_BG,
          }),
    },
    components: {
      Layout: {
        bodyBg: isDark ? DARK.layout : LIGHT.layout,
        headerBg: isDark ? DARK.layout : LIGHT.container,
        footerBg: isDark ? DARK.layout : LIGHT.layout,
      },
      ...(isDark
        ? {
            Menu: {
              darkItemBg: DARK.elevated,
              darkSubMenuItemBg: DARK.elevated,
            },
          }
        : {}),
      Button: {
        borderRadius: 6,
      },
      Card: {
        borderRadiusLG: 8,
      },
    },
  }
}
