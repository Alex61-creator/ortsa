import '@testing-library/jest-dom/vitest'

const ls: Record<string, string> = {}
const localStorageMock: Storage = {
  get length() {
    return Object.keys(ls).length
  },
  clear: () => {
    for (const k of Object.keys(ls)) delete ls[k]
  },
  getItem: (k: string) => (k in ls ? ls[k] : null),
  setItem: (k: string, v: string) => {
    ls[k] = v
  },
  removeItem: (k: string) => {
    delete ls[k]
  },
  key: (i: number) => Object.keys(ls)[i] ?? null,
}

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })
