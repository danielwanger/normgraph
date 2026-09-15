import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getNorm, getNormReferences } from '../api'
import ReferenceGraph from './ReferenceGraph'

export default function NormReader({ onLoaded }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const [norm, setNorm] = useState(null)
  const [refs, setRefs] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setNorm(null)
    setRefs(null)
    setError(null)

    Promise.all([getNorm(id), getNormReferences(id)])
      .then(([normData, refsData]) => {
        if (cancelled) return
        setNorm(normData)
        setRefs(refsData)
        onLoaded?.(normData)
      })
      .catch((err) => !cancelled && setError(err.message))

    return () => { cancelled = true }
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="error">Fehler beim Laden: {error}</div>
  if (!norm) return <div className="loading">Lade Norm …</div>

  const gliederung = (norm.gliederung || []).join(' → ')

  return (
    <div className="reader-inner">
      <div className="breadcrumb">
        <Link to={`/gesetz/${norm.law_slug}`}>{norm.law_title}</Link>
        {gliederung ? ` → ${gliederung}` : ''}
      </div>

      <div className="norm-header">
        <h2 className="norm-bez">{norm.bezeichnung}</h2>
        {norm.ueberschrift && <h3 className="norm-titel">{norm.ueberschrift}</h3>}
      </div>

      <div className={`norm-text ${norm.weggefallen ? 'weggefallen' : ''}`}>
        {norm.weggefallen ? '(weggefallen)' : (norm.volltext || '(kein Volltext hinterlegt)')}
      </div>

      <div className="references-panel">
        <h3>Verweis-Graph</h3>
        <ReferenceGraph
          centerNorm={norm.bezeichnung}
          incoming={refs.wird_zitiert_von}
          outgoing={refs.verweist_auf}
        />

        <div className="ref-group" style={{ marginTop: 20 }}>
          <h3>Verweist auf</h3>
          {refs.verweist_auf.length ? (
            <div className="ref-list">
              {refs.verweist_auf.map((r) => (
                <RefChip key={r.id} r={r} onClick={() => navigate(`/norm/${r.id}`)} />
              ))}
            </div>
          ) : (
            <div className="no-refs">Keine ausgehenden Verweise gefunden.</div>
          )}
        </div>

        <div className="ref-group">
          <h3>Wird zitiert von</h3>
          {refs.wird_zitiert_von.length ? (
            <div className="ref-list">
              {refs.wird_zitiert_von.map((r) => (
                <RefChip key={r.id} r={r} onClick={() => navigate(`/norm/${r.id}`)} />
              ))}
            </div>
          ) : (
            <div className="no-refs">Keine eingehenden Verweise gefunden.</div>
          )}
        </div>
      </div>
    </div>
  )
}

function RefChip({ r, onClick }) {
  return (
    <span className="ref-chip" onClick={onClick}>
      {r.bezeichnung} <span className="slug">{r.law_slug}</span>
    </span>
  )
}