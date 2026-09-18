import { useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'
import { AlertTriangle, Brain, CheckCircle2, FileText, LayoutDashboard, Send, ShieldCheck, Sparkles, UploadCloud } from 'lucide-react'
import './App.css'

const sample = {
  customer: 'Apollo Pharmacy',
  organization: 'Apollo Hospitals',
  product: 'Amoxicillin 500 mg Capsules',
  batch: 'AMX24062',
  quantity: '12 capsules',
  category: 'Product Quality',
  summary: 'Discoloration observed on capsules',
  description: 'Customer reported discoloration in Amoxicillin 500 mg capsules from batch AMX24062. Approximately 12 capsules were affected. Customer requests investigation and replacement.'
}

function App() {
  const [form, setForm] = useState(sample)
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzed, setAnalyzed] = useState(false)
  const [saved, setSaved] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [filename, setFilename] = useState('')

  const update = (key, value) => setForm(prev => ({ ...prev, [key]: value }))

  const applyExtracted = data => setForm(prev => ({
    ...prev,
    ...Object.fromEntries(Object.entries(data || {}).filter(([, value]) => value !== null && value !== undefined))
  }))

  const analyze = async () => {
    setAnalyzing(true); setSaved(false); setError('')
    try {
      const response = await fetch(`${API}/analyze`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(form) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Analysis failed')
      setResult(data); applyExtracted(data.extracted); setAnalyzed(true)
    } catch (err) { setError(err.message || 'Could not reach the AIVOA API'); setAnalyzed(false) }
    finally { setAnalyzing(false) }
  }

  const upload = async file => {
    if (!file) return
    setFilename(file.name); setAnalyzing(true); setSaved(false); setError('')
    try {
      const body = new FormData(); body.append('file', file)
      const response = await fetch(`${API}/analyze-document`, { method: 'POST', body })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Document analysis failed')
      setResult(data); applyExtracted(data.extracted); setAnalyzed(true)
    } catch (err) { setError(err.message || 'Could not analyze the document'); setAnalyzed(false) }
    finally { setAnalyzing(false) }
  }

  const commit = async () => {
    setError('')
    try {
      const response = await fetch(`${API}/complaints`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(form) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Could not commit complaint')
      setSaved(true)
    } catch (err) { setError(err.message || 'Could not save the complaint') }
  }

  const submit = e => { e.preventDefault(); analyze() }

  const risk = result?.risk?.level || '—'
  const completeness = result?.validation?.completeness ?? 0
  const classification = result?.classification?.defect_type
    ? `${result.classification.defect_type} / ${result.classification.category || form.category || 'Product Quality'}`
    : 'Pending classification'
  const actions = result?.recommendation?.actions || ['Review batch records', 'Check complaint history']

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark">A</div><div><strong>AIVOA</strong><span>Quality Management System</span></div></div>
        <nav><button className="active"><LayoutDashboard size={16}/> Complaint Workspace</button><button>Complaint History</button><button>Analytics</button></nav>
        <div className="user-chip"><span className="status-dot"/> QA Workspace</div>
      </header>

      <main>
        <section className="hero">
          <div>
            <p className="eyebrow"><Sparkles size={15}/> AI-ASSISTED QUALITY WORKFLOW</p>
            <h1>Complaint Intelligence<br/><span>for faster QA decisions.</span></h1>
            <p className="hero-copy">Capture customer complaints, structure critical information, and surface risk signals before committing a record to the QMS.</p>
          </div>
          <div className="hero-card"><div className="mini-icon"><ShieldCheck size={22}/></div><div><strong>Controlled workflow</strong><p>AI recommendations remain subject to QA review.</p></div></div>
        </section>

        <div className="workspace">
          <section className="panel intake">
            <div className="panel-head"><div><span className="step">01</span><div><h2>Complaint intake</h2><p>Enter the complaint details or start from a source document.</p></div></div><button className="ghost" onClick={() => setForm(sample)}>Load sample</button></div>
            <form onSubmit={submit}>
              <div className="source-row"><div className="source active"><FileText size={18}/><div><strong>Manual entry</strong><span>Structured complaint form</span></div></div><label className="source upload"><UploadCloud size={18}/><div><strong>Upload document</strong><span>PDF, TXT or EML</span></div><input type="file" accept=".pdf,.docx,.txt,.eml" onChange={e => upload(e.target.files?.[0])}/></label></div>
              <div className="form-grid">
                <Field label="Customer name" value={form.customer} onChange={v=>update('customer',v)}/>
                <Field label="Organization" value={form.organization} onChange={v=>update('organization',v)}/>
                <Field label="Product name" value={form.product} onChange={v=>update('product',v)}/>
                <Field label="Batch / Lot number" value={form.batch} onChange={v=>update('batch',v)}/>
                <Field label="Affected quantity" value={form.quantity} onChange={v=>update('quantity',v)}/>
                <Field label="Complaint category" value={form.category} onChange={v=>update('category',v)}/>
                <Field label="Defect summary" value={form.summary} onChange={v=>update('summary',v)} wide/>
                <label className="field wide"><span>Complaint description</span><textarea value={form.description} onChange={e=>update('description',e.target.value)} rows="5"/></label>
              </div>
              <div className="form-actions"><span><CheckCircle2 size={16}/> Draft can be reviewed before QMS commitment</span><button className="primary" type="submit"><Brain size={17}/>{analyzing ? 'Analyzing…' : 'Analyze complaint'}<Send size={15}/></button></div>
            </form>{error && <div className="error-banner">{error}</div>}
          </section>

          <aside className="panel copilot">
            <div className="panel-head"><div><span className="step">02</span><div><h2>AI Copilot</h2><p>Structured review and risk signals.</p></div></div><span className="live">LIVE</span></div>
            {!analyzed ? <div className="empty-state"><div className="ai-orb"><Brain size={28}/></div><h3>Ready for analysis</h3><p>Submit the complaint to extract fields, validate completeness, classify the issue and assess preliminary risk.</p><div className="pipeline"><span>Extract</span><i>→</i><span>Validate</span><i>→</i><span>Classify</span><i>→</i><span>Risk</span></div></div> :
              <div className="analysis">
                <div className="risk-card"><div><span className="label">PRELIMINARY RISK</span><strong>{risk}</strong></div><AlertTriangle size={24}/></div>
                <div className="score"><div><span>Completeness</span><strong>{completeness}%</strong></div><div className="progress"><i style={{width: `${completeness}%`}}/></div></div>
                <div className="insight"><span>CLASSIFICATION</span><strong>{classification}</strong><p>{result?.classification?.rationale || "QA review is required before final disposition."}</p></div>
                <div className="insight"><span>RECOMMENDED ACTIONS</span>{actions.slice(0, 3).map((action, i) => <strong key={i}>• {action}</strong>)}<p>{result?.recommendation?.rationale || "Recommendations are provisional and require QA review."}</p></div>
                <button className="commit" onClick={commit}>{saved ? <><CheckCircle2 size={17}/> Committed to QMS</> : 'Commit reviewed complaint to QMS'}</button>
              </div>}
          </aside>
        </div>
        <section className="workflow"><div><span>03</span><strong>Human review</strong><p>QA validates AI findings before final disposition.</p></div><div><span>04</span><strong>Controlled record</strong><p>Commit the reviewed complaint into the QMS database.</p></div><div><span>05</span><strong>Traceable action</strong><p>Recommendations guide investigation and escalation.</p></div></section>
      </main>
      <footer>AIVOA Complaint Management <span>•</span> AI-assisted, human-controlled quality workflow</footer>
    </div>
  )
}

function Field({label,value,onChange,wide=false}) {
  return <label className={'field '+(wide?'wide':'')}><span>{label}</span><input value={value} onChange={e=>onChange(e.target.value)}/></label>
}

export default App
