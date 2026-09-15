const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch { /* ignore */ }
    throw new Error(detail)
  }
  return res.json()
}

export function searchNorms(q, { limit = 15, lawSlug = null } = {}) {
  const params = new URLSearchParams({ q, limit: String(limit) })
  if (lawSlug) params.set('law_slug', lawSlug)
  return get(`/search?${params.toString()}`)
}

export function getNorm(id) {
  return get(`/norms/${id}`)
}

export function getNormReferences(id) {
  return get(`/norms/${id}/references`)
}

export function listLaws(q = null) {
  const params = q ? `?${new URLSearchParams({ q }).toString()}` : ''
  return get(`/laws${params}`)
}

export function listNormsForLaw(slug) {
  return get(`/laws/${encodeURIComponent(slug)}/norms`)
}

export { API_BASE }