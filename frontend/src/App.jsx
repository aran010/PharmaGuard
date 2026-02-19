import { useState, useRef, useCallback } from 'react'
import './App.css'
import { exportToCSV, exportToPDF } from './utils/export'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SUPPORTED_DRUGS = [
  'CODEINE',
  'CLOPIDOGREL',
  'WARFARIN',
  'SIMVASTATIN',
  'AZATHIOPRINE',
  'FLUOROURACIL',
  'TRAMADOL',
  '5-FU',
]

const RISK_COLORS = {
  Safe: 'safe',
  'Adjust Dosage': 'adjust',
  Toxic: 'toxic',
  Ineffective: 'ineffective',
  Unknown: 'unknown',
}

const RISK_EMOJI = {
  Safe: '🟢',
  'Adjust Dosage': '🟡',
  Toxic: '🔴',
  Ineffective: '🟠',
  Unknown: '⚪',
}

const PHENOTYPE_LABELS = {
  PM: 'Poor Metabolizer',
  IM: 'Intermediate Metabolizer',
  NM: 'Normal Metabolizer',
  RM: 'Rapid Metabolizer',
  URM: 'Ultra-Rapid Metabolizer',
  PF: 'Poor Function',
  DF: 'Decreased Function',
  NF: 'Normal Function',
}

function App() {
  const [file, setFile] = useState(null)
  const [drug, setDrug] = useState('')
  const [customDrug, setCustomDrug] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [copied, setCopied] = useState(false)

  // Expandable sections
  const [expanded, setExpanded] = useState({
    profile: true,
    explanation: true,
    json: false,
  })

  const fileInputRef = useRef(null)

  const toggleExpand = (key) => {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  // File handling
  const handleFileSelect = (f) => {
    if (f) {
      setFile(f)
      setError(null)
    }
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    handleFileSelect(f)
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragOver(false)
  }, [])

  const removeFile = () => {
    setFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const getSelectedDrug = () => {
    if (drug === 'custom') return customDrug.trim().toUpperCase()
    return drug
  }

  // Analysis
  const handleAnalyze = async () => {
    const selectedDrug = getSelectedDrug()
    if (!file || !selectedDrug) {
      setError('Please upload a VCF file and select a drug')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('drug', selectedDrug)

      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => null)
        throw new Error(errData?.detail || `Server error: ${res.status}`)
      }

      const data = await res.json()
      setResult(data)
      setExpanded({ profile: true, explanation: true, json: false })
    } catch (err) {
      setError(err.message || 'Analysis failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  // Download / Copy
  const downloadJSON = () => {
    if (!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pharmaguard_${result.drug}_${result.patient_id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const copyJSON = async () => {
    if (!result) return
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
      const ta = document.createElement('textarea')
      ta.value = JSON.stringify(result, null, 2)
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const resetAnalysis = () => {
    setResult(null)
    setFile(null)
    setDrug('')
    setCustomDrug('')
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }

  const riskLabel = result?.risk_assessment?.risk_label || 'Unknown'
  const riskClass = RISK_COLORS[riskLabel] || 'unknown'

  return (
    <>
      <div className="app-bg" />
      <div className="app-container">

        {/* Header */}
        <header className="header">
          <div className="header-badge">
            <span className="dot" />
            Pharmacogenomics Analysis Platform
          </div>
          <h1>PharmaGuard</h1>
          <p>Upload your VCF genetic data, select a drug, and get AI-powered pharmacogenomic risk analysis in seconds.</p>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="error-banner">
            <span className="error-icon">⚠️</span>
            <span className="error-text">{error}</span>
          </div>
        )}

        {!result && !loading && (
          <>
            {/* Upload Card */}
            <div className="card">
              <div className="card-title">
                <span className="icon">🧬</span>
                Upload VCF File
              </div>

              <div
                className={`upload-zone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => !file && fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".vcf,.vcf.gz,.txt"
                  hidden
                  onChange={(e) => handleFileSelect(e.target.files[0])}
                />
                {file ? (
                  <div className="file-info">
                    <span style={{ fontSize: '1.5rem' }}>✅</span>
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{formatFileSize(file.size)}</span>
                    <button className="remove-btn" onClick={(e) => { e.stopPropagation(); removeFile(); }}>
                      ✕ Remove
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="upload-icon">📄</div>
                    <h3>Drop your VCF file here or click to browse</h3>
                    <p>Supports all VCF formats (v3.x, v4.x, etc.) • Max 10MB</p>
                  </>
                )}
              </div>
            </div>

            {/* Drug Selector Card */}
            <div className="card">
              <div className="card-title">
                <span className="icon">💊</span>
                Select Drug
              </div>

              <div className="drug-selector-group">
                <div>
                  <label htmlFor="drug-select">Drug to analyze</label>
                  <select
                    id="drug-select"
                    className="drug-selector"
                    value={drug}
                    onChange={(e) => setDrug(e.target.value)}
                  >
                    <option value="">— Select a drug —</option>
                    {SUPPORTED_DRUGS.map((d) => (
                      <option key={d} value={d}>{d.charAt(0) + d.slice(1).toLowerCase()}</option>
                    ))}
                    <option value="custom">Other (custom)</option>
                  </select>
                </div>
                {drug === 'custom' && (
                  <div>
                    <label htmlFor="custom-drug">Custom drug name</label>
                    <input
                      id="custom-drug"
                      type="text"
                      className="drug-input"
                      placeholder="e.g., Tramadol"
                      value={customDrug}
                      onChange={(e) => setCustomDrug(e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Analyze Button */}
            <button
              className="analyze-btn"
              disabled={!file || (!drug || (drug === 'custom' && !customDrug.trim()))}
              onClick={handleAnalyze}
            >
              🔬 Analyze Genetic Variants
            </button>
          </>
        )}

        {/* Loading State */}
        {loading && (
          <div className="loading-container">
            <div className="dna-spinner" />
            <h3>Analyzing Genetic Variants...</h3>
            <p>Parsing VCF • Running risk engine • Generating AI explanation</p>
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div className="results-section">

            {/* Risk Badge */}
            <div className="risk-badge-container">
              <div className={`risk-badge ${riskClass}`}>
                <span>{RISK_EMOJI[riskLabel] || '⚪'}</span>
                {riskLabel}
              </div>
              <div className="risk-meta">
                <div className="risk-meta-item">
                  <div className="label">Drug</div>
                  <div className="value">{result.drug}</div>
                </div>
                <div className="risk-meta-item">
                  <div className="label">Confidence</div>
                  <div className="value">{(result.risk_assessment.confidence_score * 100).toFixed(0)}%</div>
                </div>
                <div className="risk-meta-item">
                  <div className="label">Severity</div>
                  <div className="value">{result.risk_assessment.severity}</div>
                </div>
                <div className="risk-meta-item">
                  <div className="label">Patient ID</div>
                  <div className="value">{result.patient_id}</div>
                </div>
              </div>
            </div>

            {/* Clinical Recommendation */}
            <div className="card">
              <div className="card-title">
                <span className="icon">🏥</span>
                Clinical Recommendation
              </div>
              <div className="recommendation-grid">
                <div className="recommendation-item">
                  <div className="rec-label">Action</div>
                  <div className="rec-value">{result.clinical_recommendation.action}</div>
                </div>
                <div className="recommendation-item">
                  <div className="rec-label">Dosing Adjustment</div>
                  <div className="rec-value">{result.clinical_recommendation.dosing_adjustment}</div>
                </div>
                <div className="recommendation-item full-width">
                  <div className="rec-label">Monitoring</div>
                  <div className="rec-value">{result.clinical_recommendation.monitoring}</div>
                </div>
              </div>
            </div>

            {/* Pharmacogenomic Profile */}
            <div className="expand-section">
              <div className="expand-header" onClick={() => toggleExpand('profile')}>
                <h4><span>🧬</span> Pharmacogenomic Profile</h4>
                <span className={`expand-arrow ${expanded.profile ? 'open' : ''}`}>▼</span>
              </div>
              {expanded.profile && (
                <div className="expand-body">
                  <div className="profile-grid">
                    <div className="profile-item">
                      <div className="p-label">Gene</div>
                      <div className="p-value">{result.pharmacogenomic_profile.primary_gene}</div>
                    </div>
                    <div className="profile-item">
                      <div className="p-label">Diplotype</div>
                      <div className="p-value">{result.pharmacogenomic_profile.diplotype}</div>
                    </div>
                    <div className="profile-item">
                      <div className="p-label">Phenotype</div>
                      <div className="p-value">{result.pharmacogenomic_profile.phenotype}</div>
                    </div>
                    <div className="profile-item" style={{ gridColumn: '1 / -1' }}>
                      <div className="p-label">Phenotype Meaning</div>
                      <div className="p-value" style={{ fontSize: '0.82rem', fontWeight: 500 }}>
                        {PHENOTYPE_LABELS[result.pharmacogenomic_profile.phenotype] || result.pharmacogenomic_profile.phenotype}
                      </div>
                    </div>
                  </div>

                  {result.pharmacogenomic_profile.detected_variants.length > 0 && (
                    <table className="variants-table">
                      <thead>
                        <tr>
                          <th>rsID</th>
                          <th>Gene</th>
                          <th>Star Allele</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.pharmacogenomic_profile.detected_variants.map((v, i) => (
                          <tr key={i}>
                            <td>{v.rsid}</td>
                            <td>{v.gene}</td>
                            <td>{v.star}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>

            {/* AI Clinical Explanation */}
            {result.llm_generated_explanation && Object.keys(result.llm_generated_explanation).length > 0 && (
              <div className="expand-section">
                <div className="expand-header" onClick={() => toggleExpand('explanation')}>
                  <h4><span>🤖</span> AI Clinical Explanation</h4>
                  <span className={`expand-arrow ${expanded.explanation ? 'open' : ''}`}>▼</span>
                </div>
                {expanded.explanation && (
                  <div className="expand-body explanation-content">
                    {result.llm_generated_explanation.summary && (
                      <>
                        <h5>Summary</h5>
                        <p>{result.llm_generated_explanation.summary}</p>
                      </>
                    )}
                    {result.llm_generated_explanation.biological_mechanism && (
                      <>
                        <h5>Biological Mechanism</h5>
                        <p>{result.llm_generated_explanation.biological_mechanism}</p>
                      </>
                    )}
                    {result.llm_generated_explanation.clinical_significance && (
                      <>
                        <h5>Clinical Significance</h5>
                        <p>{result.llm_generated_explanation.clinical_significance}</p>
                      </>
                    )}
                    {result.llm_generated_explanation.cpic_guideline_reference && (
                      <>
                        <h5>CPIC Guideline Reference</h5>
                        <p>{result.llm_generated_explanation.cpic_guideline_reference}</p>
                      </>
                    )}
                    {result.llm_generated_explanation.alternative_recommendations?.length > 0 && (
                      <>
                        <h5>Alternative Recommendations</h5>
                        <ul>
                          {result.llm_generated_explanation.alternative_recommendations.map((rec, i) => (
                            <li key={i}>{rec}</li>
                          ))}
                        </ul>
                      </>
                    )}

                  </div>
                )}
              </div>
            )}

            {/* Raw JSON */}
            <div className="expand-section">
              <div className="expand-header" onClick={() => toggleExpand('json')}>
                <h4><span>{ }</span> Raw JSON Output</h4>
                <span className={`expand-arrow ${expanded.json ? 'open' : ''}`}>▼</span>
              </div>
              {expanded.json && (
                <div className="expand-body">
                  <div className="json-container">
                    <pre>{JSON.stringify(result, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>

            {/* Quality Metrics */}
            <div className="card" style={{ marginTop: '0.5rem' }}>
              <div className="card-title">
                <span className="icon">📊</span>
                Quality Metrics
              </div>
              <div className="profile-grid">
                <div className="profile-item">
                  <div className="p-label">VCF Parsing</div>
                  <div className="p-value" style={{ color: result.quality_metrics.vcf_parsing_success ? 'var(--risk-safe)' : 'var(--risk-toxic)' }}>
                    {result.quality_metrics.vcf_parsing_success ? '✓ Success' : '✗ Errors'}
                  </div>
                </div>
                <div className="profile-item">
                  <div className="p-label">Variants Found</div>
                  <div className="p-value">{result.quality_metrics.variants_detected}</div>
                </div>
                <div className="profile-item">
                  <div className="p-label">Genes Analyzed</div>
                  <div className="p-value">{result.quality_metrics.genes_analyzed}</div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="actions-bar">
              <button className="action-btn download" onClick={() => exportToPDF(result)}>
                📄 Download PDF
              </button>
              <button className="action-btn download" style={{ backgroundColor: '#2563eb' }} onClick={() => exportToCSV(result)}>
                📊 Download CSV
              </button>
              <button className="action-btn download" style={{ backgroundColor: '#4b5563' }} onClick={downloadJSON}>
                ⚙️ JSON
              </button>
              <button className={`action-btn copy ${copied ? 'copied' : ''}`} onClick={copyJSON}>
                {copied ? '✅ Copied!' : '📋 Copy JSON'}
              </button>
              <button className="action-btn new-analysis" onClick={resetAnalysis}>
                🔄 New Analysis
              </button>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="footer">
          <p>PharmaGuard — AI-Powered Pharmacogenomics Analysis • Built for RIFT 2026</p>
          <p style={{ marginTop: '0.25rem' }}>⚠️ For research and educational purposes only. Not a substitute for clinical advice.</p>
        </footer>
      </div>
    </>
  )
}

export default App
