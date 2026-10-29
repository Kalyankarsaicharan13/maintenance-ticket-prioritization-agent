import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Gauge,
  Leaf,
  ListFilter,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Wind,
  Zap,
} from 'lucide-react'
import './styles.css'

const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 }
const assetIcons = { solar: Zap, wind: Wind, hydro: Activity, grid: Radio }

function formatCategory(category = '') {
  return category.replaceAll('_', ' ')
}

function Severity({ value }) {
  return <span className={`severity severity-${value || 'medium'}`}><span />{value || 'medium'}</span>
}

function App() {
  const today = new Date().toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).toUpperCase()
  const [tickets, setTickets] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [selectedId, setSelectedId] = useState('')
  const [description, setDescription] = useState('')
  const [assetType, setAssetType] = useState('solar')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [connected, setConnected] = useState(false)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')

  async function runTriage(text = description, asset = assetType) {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    try {
      const response = await fetch('/api/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: text, asset_type: asset }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail?.[0]?.msg || body.detail || 'Could not analyze this ticket.')
      }
      setResult(await response.json())
    } catch (requestError) {
      setError(requestError.message || 'The triage service is unavailable.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    async function loadDashboard() {
      try {
        const [ticketResponse, metricResponse, healthResponse] = await Promise.all([
          fetch('/api/tickets'),
          fetch('/api/metrics'),
          fetch('/api/health'),
        ])
        if (!ticketResponse.ok || !metricResponse.ok || !healthResponse.ok) throw new Error('API unavailable')
        const [ticketData, metricData] = await Promise.all([ticketResponse.json(), metricResponse.json()])
        if (!active) return
        const ordered = [...ticketData].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity])
        setTickets(ordered)
        setMetrics(metricData)
        setConnected(true)
        if (ordered[0]) {
          setSelectedId(ordered[0].ticket_id)
          setDescription(ordered[0].description)
          setAssetType(ordered[0].asset_type)
          runTriage(ordered[0].description, ordered[0].asset_type)
        }
      } catch {
        if (active) setError('Unable to connect to the API. Start FastAPI and the Vite dev server.')
      }
    }
    loadDashboard()
    return () => { active = false }
  }, [])

  const filteredTickets = tickets.filter((ticket) => {
    const matchesSeverity = filter === 'all' || ticket.severity === filter
    const query = search.trim().toLowerCase()
    return matchesSeverity && (!query || `${ticket.ticket_id} ${ticket.asset_type} ${ticket.description} ${ticket.category}`.toLowerCase().includes(query))
  })
  const criticalCount = tickets.filter((ticket) => ticket.severity === 'critical').length
  const highCount = tickets.filter((ticket) => ticket.severity === 'high').length
  const manualCount = tickets.filter((ticket) => ticket.disposition === 'manual_review').length

  function selectTicket(ticket) {
    setSelectedId(ticket.ticket_id)
    setDescription(ticket.description)
    setAssetType(ticket.asset_type)
    runTriage(ticket.description, ticket.asset_type)
  }

  function handleSubmit(event) {
    event.preventDefault()
    runTriage()
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#overview" aria-label="Fielddesk home">
          <span className="brand-mark"><Leaf size={17} strokeWidth={2.2} /></span>
          <span>fielddesk<span className="brand-period">.</span></span>
        </a>
        <div className="topbar-center"><span className="workspace-mark"><Wind size={15} /></span> Renewable operations <span className="topbar-divider">/</span> Maintenance</div>
        <div className={`connection ${connected ? 'is-connected' : ''}`}><span />{connected ? 'Systems live' : 'Connecting'}</div>
      </header>

      <main id="overview" className="content">
        <div className="page-heading">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" /> FIELD OPERATIONS <span className="eyebrow-date">| {today}</span></div>
            <h1>Maintenance desk</h1>
            <p className="page-subtitle">Triage and route asset issues across your renewable fleet.</p>
          </div>
          <button className="quiet-button" type="button" title="Refresh ticket data" onClick={() => window.location.reload()}><RefreshCw size={15} /><span>Refresh data</span></button>
        </div>

        <section className="stats-row" aria-label="Ticket overview">
          <article className="stat-item stat-total">
            <div className="stat-top"><span>OPEN TICKETS</span><ListFilter size={15} /></div>
            <div className="stat-value">{tickets.length.toString().padStart(2, '0')}<span className="stat-unit">in queue</span></div>
            <div className="stat-caption">Bundled demonstration dataset</div>
          </article>
          <article className="stat-item stat-critical">
            <div className="stat-top"><span>CRITICAL</span><AlertTriangle size={15} /></div>
            <div className="stat-value">{criticalCount.toString().padStart(2, '0')}<span className="stat-unit">require urgent review</span></div>
            <div className="stat-caption">Confirm against current site conditions</div>
          </article>
          <article className="stat-item stat-high">
            <div className="stat-top"><span>HIGH PRIORITY</span><ArrowDownRight size={15} /></div>
            <div className="stat-value">{highCount.toString().padStart(2, '0')}<span className="stat-unit">need attention</span></div>
            <div className="stat-caption">Escalate to asset maintenance teams</div>
          </article>
          <article className="stat-item stat-eval">
            <div className="stat-top"><span>SAMPLE LABEL MATCH</span><ShieldCheck size={15} /></div>
            <div className="stat-value">{metrics ? `${Math.round(metrics.category_accuracy * 100)}%` : '--'}<span className="stat-unit">category match</span></div>
            <div className="stat-caption">{metrics?.sample_count ?? 0} tickets · in-sample check</div>
          </article>
        </section>

        <div className="section-bar">
          <div className="section-title"><span className="section-index">01</span><h2>Ticket queue</h2><span className="queue-count">{filteredTickets.length} RECORDS</span></div>
          <div className="queue-controls">
            <label className="search-box"><Search size={15} /><input aria-label="Search tickets" placeholder="Search tickets" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
            <label className="filter-box"><ListFilter size={14} /><select aria-label="Filter by severity" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">All severity</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select><ChevronDown size={13} /></label>
          </div>
        </div>

        <div className="work-grid">
          <section className="queue-panel" aria-label="Maintenance ticket queue">
            <div className="table-wrap">
              <table>
                <thead><tr><th>Ticket</th><th>Asset / issue</th><th>Category</th><th>Severity</th><th aria-label="Select" /></tr></thead>
                <tbody>
                  {filteredTickets.map((ticket) => {
                    const AssetIcon = assetIcons[ticket.asset_type] || Gauge
                    return <tr key={ticket.ticket_id} className={selectedId === ticket.ticket_id ? 'selected-row' : ''} onClick={() => selectTicket(ticket)}>
                      <td className="ticket-id">{ticket.ticket_id}</td>
                      <td><div className="asset-cell"><span className={`asset-icon asset-${ticket.asset_type}`}><AssetIcon size={15} /></span><span className="asset-copy"><strong>{ticket.asset_type}</strong><span>{ticket.description}</span></span></div></td>
                      <td><span className="category-label">{formatCategory(ticket.category)}</span></td>
                      <td><Severity value={ticket.severity} /></td>
                      <td><button className="row-open" type="button" aria-label={`Analyze ${ticket.ticket_id}`} onClick={(event) => { event.stopPropagation(); selectTicket(ticket) }}><ArrowRight size={15} /></button></td>
                    </tr>
                  })}
                  {!filteredTickets.length && <tr><td className="empty-cell" colSpan="5">No tickets match this view.</td></tr>}
                </tbody>
              </table>
            </div>
            <div className="queue-foot"><span><span className="live-dot" /> LIVE CLASSIFICATION</span><span>Sorted by severity <ArrowDownRight size={12} /></span></div>
          </section>

          <section className="triage-panel" aria-label="Ticket triage">
            <div className="triage-heading"><div><div className="eyebrow"><span className="section-index">02</span> AGENT WORKSPACE</div><h2>Analyze a ticket</h2></div><span className="agent-badge"><Sparkles size={13} /> RULE + RETRIEVAL</span></div>
            <form className="triage-form" onSubmit={handleSubmit}>
              <label className="field-label" htmlFor="asset-type">ASSET TYPE</label>
              <div className="select-wrap"><select id="asset-type" value={assetType} onChange={(event) => setAssetType(event.target.value)}><option value="solar">Solar</option><option value="wind">Wind</option><option value="hydro">Hydro</option><option value="grid">Grid</option><option value="unknown">Unknown / other</option></select><ChevronDown size={15} /></div>
              <label className="field-label description-label" htmlFor="ticket-description">TICKET DESCRIPTION</label>
              <textarea id="ticket-description" value={description} onChange={(event) => { setDescription(event.target.value); setSelectedId('') }} placeholder="Describe the observed fault, asset, and operational impact..." minLength={8} maxLength={2000} required />
              <div className="form-footer"><span>{description.length}/2000 characters</span><button className="analyze-button" type="submit" disabled={loading || description.trim().length < 8}>{loading ? <><RefreshCw size={15} className="spin" /> Analyzing</> : <><Sparkles size={15} /> Run triage</>}</button></div>
            </form>

            {error && <div className="error-banner" role="alert"><CircleHelp size={16} />{error}</div>}

            {result ? <div className="result-block" aria-live="polite">
              <div className="result-topline"><span>TRIAGE RESULT</span><span className={`disposition disposition-${result.disposition}`}>{result.disposition === 'routed' ? <Check size={12} /> : <CircleHelp size={12} />}{result.disposition.replaceAll('_', ' ')}</span></div>
              <div className="result-priority"><Severity value={result.severity} /><span className="confidence">{result.confidence} confidence</span><span className="result-category">{formatCategory(result.category)}</span></div>
              <div className="result-detail"><span className="detail-label">PROBABLE ROOT CAUSE</span><p>{result.probable_root_cause}</p></div>
              <div className="result-detail action-detail"><span className="detail-label">RECOMMENDED NEXT ACTION</span><p>{result.next_action}</p></div>
              <div className="route-line"><span className="route-icon"><ArrowRight size={14} /></span><span><small>ROUTE TO</small><strong>{result.route_to}</strong></span></div>
                      <div className="evidence-box"><div className="evidence-title"><Search size={13} /> CLOSEST REFERENCE <span>{result.evidence.similarity.toFixed(3)} SIMILARITY</span></div><div className="evidence-copy"><strong>{result.evidence.ticket_id} | {formatCategory(result.evidence.category)}</strong><p>{result.evidence.description}</p></div></div>
              <div className="agent-trace"><div className="trace-title"><Activity size={14} /> AGENT TRACE <span>{result.agent_steps.length} STEPS</span></div>{result.agent_steps.map((step, index) => <div className="trace-step" key={step.tool}><span className="trace-number">{String(index + 1).padStart(2, '0')}</span><span className="trace-tool">{step.tool.replaceAll('_', ' ')}</span><span className="trace-result">{step.result}</span></div>)}</div>
              <div className="safety-note"><ShieldCheck size={14} /><span>Decision support only. Verify severity and isolation requirements under site procedures.</span></div>
            </div> : <div className="result-empty"><Sparkles size={18} /><span>Choose a queue ticket or describe an issue to see triage.</span></div>}
          </section>
        </div>

        <footer className="page-footer"><span><span className="footer-mark"><Leaf size={12} /></span> FIELDDESK <span className="footer-sep">/</span> MAINTENANCE INTELLIGENCE</span><span className="footer-note"><Clock3 size={12} /> Prototype - {manualCount} tickets need manual review</span></footer>
      </main>
    </div>
  )
}

export default App

createRoot(document.getElementById('root')).render(<App />)
