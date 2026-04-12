export interface GeocodeHit {
  display_name: string
  lat: string
  lon: string
}

export async function nominatimSearch(query: string): Promise<GeocodeHit[]> {
  const q = query.trim()
  if (q.length < 2) return []
  const ua =
    import.meta.env.VITE_GEOCODER_USER_AGENT ??
    'AstroGen/1.0 (https://github.com/astrogen; contact: support@example.com)'
  const url = new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('q', q)
  url.searchParams.set('format', 'json')
  url.searchParams.set('limit', '6')
  const res = await fetch(url.toString(), {
    headers: {
      Accept: 'application/json',
      'Accept-Language': 'ru',
      'User-Agent': ua,
    },
  })
  if (!res.ok) throw new Error('Geocoder error')
  const data = (await res.json()) as GeocodeHit[]
  return Array.isArray(data) ? data : []
}
