import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// ResizeObserver не реализован в jsdom — нужен polyfill для Ant Design Table
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// @ts-expect-error test polyfill
global.ResizeObserver = ResizeObserverMock

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
})

window.getComputedStyle = ((elt: Element) => {
  return {
    getPropertyValue: () => '',
    display: '',
    appearance: ['INPUT', 'TEXTAREA'].includes(elt.tagName) ? 'textfield' : '',
  } as CSSStyleDeclaration
}) as typeof window.getComputedStyle
