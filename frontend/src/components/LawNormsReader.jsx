import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { listNormsForLaw } from '../api'

export default function LawNormsReader() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [norms, setNorms] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setNorms(null)
    setError(null)
    listNormsForLaw(slug).then(setNorms).catch((err) => setError(err.message))
  }, [slug])

  if (error) return <div className="error">{error}</div>
  if (!norms) return <div className="loading">Lade Gesetz …</div>

  return (
    <div className="reader-inner">
      <div className="norm-header">
        <h2 className="norm-bez">{slug}</h2>
        <h3 className="norm-titel">{norms.length} Normen — Dokumentreihenfolge</h3>
      </div>
      {norms.map((n) => (
        <div
          key={n.id}
          className="result-item"
          style={{ borderLeft: 'none', margin: '0 -24px' }}
          onClick={() => navigate(`/norm/${n.id}`)}
        >
          <div className="bez">{n.bezeichnung}</div>
          <div className="titel">{n.ueberschrift || (n.weggefallen ? '(weggefallen)' : '(ohne Überschrift)')}</div>
        </div>
      ))}
    </div>
  )
}