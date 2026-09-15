import { useNavigate } from 'react-router-dom'

export default function ResultsList({ results, activeId }) {
  const navigate = useNavigate()

  if (results === null) {
    return (
      <div className="empty-state">
        Gib eine Frage oder ein Stichwort ein — die Suche findet inhaltlich
        passende Normen, nicht nur exakte Wortübereinstimmungen.
      </div>
    )
  }

  if (results.length === 0) {
    return <div className="empty-state">Keine passenden Normen gefunden.</div>
  }

  return (
    <div className="results">
      {results.map((item) => (
        <div
          key={item.id}
          className={`result-item ${item.id === activeId ? 'active' : ''}`}
          onClick={() => navigate(`/norm/${item.id}`)}
        >
          <div className="bez">
            {item.bezeichnung} <span className="slug">{item.law_slug}</span>
          </div>
          <div className="titel">{item.ueberschrift || '(ohne Überschrift)'}</div>
          <div className="law">{item.law_title}</div>
          <div className="score">Ähnlichkeit: {(item.similarity * 100).toFixed(1)}%</div>
        </div>
      ))}
    </div>
  )
}