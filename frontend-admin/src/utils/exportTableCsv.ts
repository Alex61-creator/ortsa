function escapeCell(value: string) {
  const safe = value.replace(/"/g, '""')
  return `"${safe}"`
}

export function exportFirstTableAsCsv(filename = 'admin-export.csv') {
  const table = document.querySelector('table')
  if (!table) return false
  const rows = Array.from(table.querySelectorAll('tr'))
  const lines = rows.map((row) => {
    const cells = Array.from(row.querySelectorAll('th,td'))
    const values = cells.map((c) => escapeCell((c.textContent ?? '').trim()))
    return values.join(',')
  })
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
  return true
}
