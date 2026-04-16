import { api } from '@/api/client'

export async function downloadAdminCsv(
  path: string,
  filename: string,
  params?: Record<string, string | number | undefined>,
) {
  const clean: Record<string, string | number> = {}
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) clean[k] = v
    }
  }
  const res = await api.get(path, { params: clean, responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
