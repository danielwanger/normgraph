import { useEffect, useState } from 'react'
import { listLaws } from '../api'

export default function SearchPanel({ onSearch, status }) {
  const [query, setQuery] = useState('')
  const [lawSlug, setLawSlug] = useState('')
  const [laws, setLaws] = useState([])

  // Gesetzesliste einmalig für den Filter laden. Bei ~4.5k Gesetzen ist das
  // eine größere Liste — für die Erstversion ok, könnte man später mit einem
  // durchsuchbaren Combobox-Widget statt <select> ersetzen.
  useEffect(() => {
    listLaws().then(setLaws).catch(() => {})
  }, [])

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) {
      onSearch(null)
      return
    }
    const timer = setTimeout(() => {
      onSearch({ q, lawSlug: lawSlug || null })
    }, 400)
    return () => clearTimeout(timer)
  }, [query, lawSlug]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <div className="search-box">
        <input
          type="text"
          placeholder="z.B. Widerrufsrecht bei Onlinekäufen …"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <select value={lawSlug} onChange={(e) => setLawSlug(e.target.value)}>
          <option value="">Alle Gesetze</option>
          {laws.map((l) => (
            <option key={l.id} value={l.slug}>{l.slug} — {l.title}</option>
          ))}
        </select>
      </div>
      <div className="search-status">{status}</div>
    </>
  )
}