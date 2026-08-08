const API = process.env.NEXT_PUBLIC_API_URL || 'https://aramesh129-fightiq-api.hf.space'

export async function fetchUpcoming() {
  const res = await fetch(`${API}/api/upcoming`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch upcoming')
  return res.json()
}

export async function fetchHistory(page = 1, limit = 20) {
  const res = await fetch(`${API}/api/history?page=${page}&limit=${limit}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch history')
  return res.json()
}

export async function fetchFight(boutId) {
  const res = await fetch(`${API}/api/fight/${boutId}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch fight')
  return res.json()
}

export async function fetchModelStats() {
  const res = await fetch(`${API}/api/stats`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export function initials(name) {
  if (!name) return '?'
  const parts = name.trim().split(' ')
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function initialsFromParts(firstName, lastName) {
  return `${(firstName || '')[0] || ''}${(lastName || '')[0] || ''}`.toUpperCase()
}

export function calcAge(birthday) {
  if (!birthday) return null
  const diff = Date.now() - new Date(birthday).getTime()
  return Math.floor(diff / (365.25 * 24 * 3600 * 1000))
}