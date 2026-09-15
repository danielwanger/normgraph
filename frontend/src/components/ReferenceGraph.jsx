import { useNavigate } from 'react-router-dom'

const WIDTH = 600
const HEIGHT = 340
const CENTER = { x: WIDTH / 2, y: HEIGHT / 2 }
const RADIUS = 130

/**
 * Zeigt die aktuelle Norm im Zentrum, eingehende Verweise im oberen Halbkreis
 * und ausgehende Verweise im unteren Halbkreis. Rein SVG-basiert (kein
 * Force-Layout) — bei max. ~10-15 Knoten pro Seite reicht ein einfaches
 * radiales Layout und bleibt vorhersagbar/performant.
 */
export default function ReferenceGraph({ centerNorm, incoming, outgoing }) {
  const navigate = useNavigate()

  const incomingNodes = layoutArc(incoming, Math.PI, 2 * Math.PI, incoming.length)
  const outgoingNodes = layoutArc(outgoing, 0, Math.PI, outgoing.length)

  const allNodes = [...incomingNodes, ...outgoingNodes]
  if (allNodes.length === 0) {
    return <div className="no-refs">Keine Verweise zum Visualisieren.</div>
  }

  return (
    <svg className="graph-svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="var(--gray-light)" />
        </marker>
      </defs>

      {/* Kanten: eingehend -> Zentrum, Zentrum -> ausgehend */}
      {incomingNodes.map((n) => (
        <line key={`e-in-${n.id}`} className="graph-edge" x1={n.x} y1={n.y} x2={CENTER.x} y2={CENTER.y} />
      ))}
      {outgoingNodes.map((n) => (
        <line key={`e-out-${n.id}`} className="graph-edge" x1={CENTER.x} y1={CENTER.y} x2={n.x} y2={n.y} />
      ))}

      {/* Zentraler Knoten */}
      <circle cx={CENTER.x} cy={CENTER.y} r={10} fill="var(--wine)" />
      <text x={CENTER.x} y={CENTER.y + 24} textAnchor="middle" className="graph-node-label" fontWeight="600">
        {centerNorm}
      </text>

      {/* Satelliten-Knoten */}
      {allNodes.map((n) => (
        <g key={n.id} onClick={() => navigate(`/norm/${n.id}`)}>
          <circle cx={n.x} cy={n.y} r={6} fill="var(--ink)" className="graph-node-circle" />
          <text
            x={n.x}
            y={n.y + (n.y < CENTER.y ? -12 : 20)}
            textAnchor="middle"
            className="graph-node-label"
          >
            {n.bezeichnung}
          </text>
        </g>
      ))}
    </svg>
  )
}

function layoutArc(nodes, startAngle, endAngle, count) {
  if (count === 0) return []
  const step = (endAngle - startAngle) / (count + 1)
  return nodes.map((n, i) => {
    const angle = startAngle + step * (i + 1)
    return {
      ...n,
      x: CENTER.x + RADIUS * Math.cos(angle),
      y: CENTER.y + RADIUS * Math.sin(angle),
    }
  })
}