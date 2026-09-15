import { useState } from 'react'
import { Routes, Route, useMatch } from 'react-router-dom'
import SearchPanel from './components/SearchPanel'
import ResultsList from './components/ResultsList'
import LawBrowser from './components/LawBrowser'
import NormReader from './components/NormReader'
import LawNormsReader from './components/LawNormsReader'
import { searchNorms } from './api'

export default function App() {
  const [mode, setMode] = useState('search') // 'search' | 'laws'
  const [results, setResults] = useState(null)
  const [searchStatus, setSearchStatus] = useState('')

  const handleSearch = (params) => {
    if (!params) {
      setResults(null)
      setSearchStatus('')
      return
    }
    setSearchStatus('Suche läuft …')
    searchNorms(params.q, { lawSlug: params.lawSlug })
      .then((data) => {
        setResults(data)
        setSearchStatus(data.length ? `${data.length} Treffer` : 'Keine Treffer — versuch es mit anderen Begriffen.')
      })
      .catch((err) => {
        setResults([])
        setSearchStatus(`Fehler: ${err.message}`)
      })
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <h1>Normgraph</h1>
          <p>Semantische Suche über deutsches Bundesrecht</p>
        </div>

        <div className="mode-tabs">
          <button className={`mode-tab ${mode === 'search' ? 'active' : ''}`} onClick={() => setMode('search')}>
            Suche
          </button>
          <button className={`mode-tab ${mode === 'laws' ? 'active' : ''}`} onClick={() => setMode('laws')}>
            Gesetze
          </button>
        </div>

        {mode === 'search' ? (
          <>
            <SearchPanel onSearch={handleSearch} status={searchStatus} />
            <ActiveIdConsumer>
              {(activeId) => <ResultsList results={results} activeId={activeId} />}
            </ActiveIdConsumer>
          </>
        ) : (
          <LawBrowser />
        )}
      </aside>

      <main className="reader">
        <Routes>
          <Route path="/" element={<Welcome />} />
          <Route path="/norm/:id" element={<NormReader />} />
          <Route path="/gesetz/:slug" element={<LawNormsReader />} />
        </Routes>
      </main>
    </div>
  )
}

function Welcome() {
  return (
    <div className="welcome">
      <h2>Wähle einen Treffer aus der Suche,<br />um eine Norm zu lesen.</h2>
    </div>
  )
}

// Liest die aktuelle Norm-ID aus der Route, damit die Trefferliste den
// gerade geöffneten Eintrag hervorheben kann. useMatch funktioniert überall
// innerhalb des Routers, anders als useParams (das einen Route-Match braucht).
function ActiveIdConsumer({ children }) {
  const match = useMatch('/norm/:id')
  return children(match ? parseInt(match.params.id, 10) : null)
}