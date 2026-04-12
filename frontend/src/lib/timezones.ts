/** IANA timezone ids compatible with backend zoneinfo validation. */
export function getSelectableTimezones(): string[] {
  try {
    const fn = (
      Intl as unknown as { supportedValuesOf?: (k: string) => string[] }
    ).supportedValuesOf
    if (typeof fn === 'function') {
      return fn.call(Intl, 'timeZone').sort()
    }
  } catch {
    /* fall through */
  }
  return [
    'UTC',
    'Europe/Moscow',
    'Europe/Kaliningrad',
    'Europe/Samara',
    'Asia/Yekaterinburg',
    'Asia/Novosibirsk',
    'Asia/Krasnoyarsk',
    'Asia/Irkutsk',
    'Asia/Yakutsk',
    'Asia/Vladivostok',
    'Asia/Magadan',
    'Asia/Kamchatka',
    'Europe/London',
    'Europe/Berlin',
    'America/New_York',
  ]
}
