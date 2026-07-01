const API = process.env.NEXT_PUBLIC_API_URL || 'https://aramesh129-fightiq-api.hf.space'

export async function fetchUpcoming() {
  const res = await fetch(`${API}/api/upcoming`, { next: { revalidate: 300 } })
  if (!res.ok) throw new Error('Failed to fetch upcoming')
  return res.json()
}

export async function fetchHistory(page = 1, limit = 20) {
  const res = await fetch(`${API}/api/history?page=${page}&limit=${limit}`, { next: { revalidate: 60 } })
  if (!res.ok) throw new Error('Failed to fetch history')
  return res.json()
}

export async function fetchFight(boutId) {
  const res = await fetch(`${API}/api/fight/${boutId}`, { next: { revalidate: 300 } })
  if (!res.ok) throw new Error('Failed to fetch fight')
  return res.json()
}

export async function fetchFighter(fighterId) {
  const res = await fetch(`${API}/api/fighter/${fighterId}`, { next: { revalidate: 300 } })
  if (!res.ok) throw new Error('Failed to fetch fighter')
  return res.json()
}

export async function fetchModelStats() {
  const res = await fetch(`${API}/api/stats`, { next: { revalidate: 3600 } })
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export function winPct(fighter) {
  const w = fighter?.wins || 0
  const l = fighter?.losses || 0
  return (w + l) > 0 ? w / (w + l) : 0.5
}

export function calcAge(birthday) {
  if (!birthday) return null
  const diff = Date.now() - new Date(birthday).getTime()
  return Math.floor(diff / (365.25 * 24 * 3600 * 1000))
}

export function initials(firstName, lastName) {
  return `${(firstName || '')[0] || ''}${(lastName || '')[0] || ''}`.toUpperCase()
}

export function formatRecord(f) {
  if (!f) return ''
  return `${f.wins || 0}-${f.losses || 0}${f.draws ? `-${f.draws}` : ''}`
}
