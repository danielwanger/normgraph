import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listLaws } from '../api'

export default function LawBrowser() {
  const [query, setQuery] = useState('')
  const [laws, setLaws] = useState([])
  const [status, setStatus] = useState('Lade Gesetze …')

  useEffect(() => {
    const timer = setTimeout(() => {
      setStatus('Lade …')
      listLaws(query.trim() || null)
        .then((data) => {
          setLaws(data)
          setStatus(`${data.length} Gesetze`)
        })
        .catch((err) => setStatus(`Fehler: ${err.message}`))
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  return (
    <>
      <div className="search-box">
        <input
          type="text"
          placeholder="Gesetz suchen (Titel oder Kürzel) …"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <div className="search-status">{status}</div>
      <div className="results">
        {laws.map((l) => (
          <Link key={l.id} to={`/gesetz/${l.slug}`} className="law-list-item" style={{ display: 'block', color: 'inherit', textDecoration: 'none' }}>
            <div className="slug">{l.slug}</div>
            <div className="title">{l.title}</div>
          </Link>
        ))}
      </div>
    </>
  )
}