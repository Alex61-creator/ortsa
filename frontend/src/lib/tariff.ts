/** Системы домов kerykeion: P Placidus, K Koch, R Regiomontanus */
export const HOUSE_SYSTEMS: { value: string; label: string }[] = [
  { value: 'P', label: 'Плацидус' },
  { value: 'K', label: 'Кох' },
  { value: 'R', label: 'Региомонтан' },
]

export function canChooseHouseSystem(tariffCode: string | null): boolean {
  if (!tariffCode) return false
  const c = tariffCode.toLowerCase()
  return c === 'standard' || c === 'premium'
}
