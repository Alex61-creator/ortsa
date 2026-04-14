import { useEffect } from 'react'

export function LandingPage() {
  useEffect(() => {
    let cancelled = false

    const mountStaticLanding = async () => {
      try {
        const response = await fetch('/static/index.html', { cache: 'no-store' })
        if (!response.ok || cancelled) return
        const html = await response.text()
        if (cancelled) return
        // Keep URL as "/" and render the exact static landing document.
        document.open()
        document.write(html)
        document.close()
      } catch {
        if (!cancelled) {
          window.location.href = '/static/index.html'
        }
      }
    }

    void mountStaticLanding()

    return () => {
      cancelled = true
    }
  }, [])

  return null
}
