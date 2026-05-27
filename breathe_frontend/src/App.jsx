import { useState, useEffect } from 'react';
import { api } from './api';
import './App.css';

function App() {
  const [rows, setRows] = useState([]);
  const [load, setLoad] = useState(true);
  const [err, setErr] = useState('');
  const [sel, setSel] = useState(null);
  const [bulk, setBulk] = useState([]);
  
  const [flagModal, setFlagModal] = useState(false);
  const [flagCode, setFlagCode] = useState('ANALYST_FLAG');
  const [flagMsg, setFlagMsg] = useState('');

  const [editMode, setEditMode] = useState(false);
  const [editVal, setEditVal] = useState('');
  const [editUnit, setEditUnit] = useState('');

  const [ingestType, setIngestType] = useState('sap');
  const [ingestPayload, setIngestPayload] = useState('');

  const loadData = async () => {
    setLoad(true);
    try {
      const data = await api.getRows();
      setRows(data);
      setErr('');
      if (data.length > 0) {
        if (sel) {
          const updated = data.find((r) => r.id === sel.id);
          setSel(updated || data[0]);
        } else {
          setSel(data[0]);
        }
      } else {
        setSel(null);
      }
    } catch (e) {
      setErr('Failed to fetch data');
    } finally {
      setLoad(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelect = (r) => {
    setSel(r);
    setEditMode(false);
    setEditVal(r.raw_val);
    setEditUnit(r.raw_unit);
  };

  const handleApprove = async (id) => {
    try {
      await api.approve(id);
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleFlag = async (id) => {
    try {
      await api.flag(id, flagCode, flagMsg);
      setFlagModal(false);
      setFlagMsg('');
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleLock = async (id) => {
    try {
      await api.lock(id);
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleEditSave = async (id) => {
    try {
      await api.edit(id, parseFloat(editVal), editUnit);
      setEditMode(false);
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleBulkApprove = async () => {
    try {
      for (const id of bulk) {
        await api.approve(id);
      }
      setBulk([]);
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleBulkLock = async () => {
    try {
      for (const id of bulk) {
        await api.lock(id);
      }
      setBulk([]);
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  };

  const toggleBulk = (id) => {
    setBulk((prev) => 
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleMockIngest = async () => {
    try {
      let p;
      if (ingestPayload.trim()) {
        p = JSON.parse(ingestPayload);
      } else {
        if (ingestType === 'sap') {
          p = { invoice_id: `SAP-${Date.now()}`, fuel_type: 'diesel', quantity: '500', unit: 'gal', date: '2026-05-27' };
        } else if (ingestType === 'utility') {
          p = { account: 'UT-100', meter: 'M-99', start_date: '2026-05-01', end_date: '2026-05-30', usage_kwh: '1500', unit: 'kwh' };
        } else {
          p = { booking_id: `NAV-${Date.now()}`, travel_type: 'flight', distance_km: '1200', date: '2026-05-27' };
        }
      }
      await api.ingest(ingestType, p);
      setIngestPayload('');
      await loadData();
    } catch (e) {
      alert('Ingestion error: ' + e.message);
    }
  };

  const totalEmissions = rows.reduce((sum, r) => sum + r.norm_val, 0);
  const pendingCount = rows.filter((r) => r.status === 'PENDING').length;
  const flaggedCount = rows.filter((r) => r.status === 'FLAGGED').length;
  const lockedCount = rows.filter((r) => r.status === 'AUDITED').length;

  return (
    <div className="esg-app">
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-logo">B</div>
          <div>
            <h1>BreatheESG</h1>
            <span className="subtitle">Audit & Ingestion Ledger</span>
          </div>
        </div>
        <div className="header-meta">
          <div className="meta-badge tenant">default-tenant</div>
          <div className="meta-badge health">DB ONLINE</div>
        </div>
      </header>

      <section className="stats-strip">
        <div className="stat-card">
          <div className="stat-label">Total Carbon Footprint</div>
          <div className="stat-value">{totalEmissions.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="stat-unit">kgCO2e</span></div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Pending Review</div>
          <div className="stat-value warning">{pendingCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Flagged Issues</div>
          <div className="stat-value danger">{flaggedCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Audited & Locked</div>
          <div className="stat-value success">{lockedCount}</div>
        </div>
      </section>

      <div className="app-workspace">
        <aside className="control-panel">
          <div className="glass-panel panel-ingest">
            <h3>Mock Ingest Sandbox</h3>
            <div className="field-group">
              <label>Pipeline Endpoint</label>
              <select value={ingestType} onChange={(e) => setIngestType(e.target.value)}>
                <option value="sap">SAP Fuel & Procurement</option>
                <option value="utility">Utility Meter Electricity</option>
                <option value="navan">Navan Corporate Travel</option>
              </select>
            </div>
            <div className="field-group">
              <label>Raw Payload JSON (Optional)</label>
              <textarea
                value={ingestPayload}
                onChange={(e) => setIngestPayload(e.target.value)}
                placeholder="Leave blank for auto-generated valid mock payload"
              />
            </div>
            <button className="btn-primary" onClick={handleMockIngest}>
              Ingest Payload
            </button>
          </div>

          {bulk.length > 0 && (
            <div className="glass-panel panel-bulk">
              <h3>Bulk Controls ({bulk.length} Selected)</h3>
              <div className="bulk-actions">
                <button className="btn-success" onClick={handleBulkApprove}>Approve All</button>
                <button className="btn-audit" onClick={handleBulkLock}>Lock All</button>
              </div>
            </div>
          )}
        </aside>

        <main className="review-board">
          <div className="glass-panel board-main">
            <div className="board-header">
              <h3>Ingestion Review Queue</h3>
              <button className="btn-secondary" onClick={loadData}>Refresh Queue</button>
            </div>

            {load ? (
              <div className="load-state">Parsing ingestion logs...</div>
            ) : err ? (
              <div className="err-state">{err}</div>
            ) : rows.length === 0 ? (
              <div className="empty-state">No ESG rows ingested yet. Use the mock ingest sandbox to get started.</div>
            ) : (
              <div className="table-wrapper">
                <table className="review-grid">
                  <thead>
                    <tr>
                      <th style={{ width: '40px' }}></th>
                      <th>Category</th>
                      <th>Scope</th>
                      <th>Raw Activity</th>
                      <th>Emissions</th>
                      <th>Date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => {
                      const hasIssues = r.issues && r.issues.length > 0;
                      const isSel = sel && sel.id === r.id;
                      return (
                        <tr
                          key={r.id}
                          className={`${isSel ? 'active' : ''} ${hasIssues ? 'flagged' : ''} ${r.status === 'AUDITED' ? 'locked' : ''}`}
                          onClick={() => handleSelect(r)}
                        >
                          <td onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={bulk.includes(r.id)}
                              disabled={r.status === 'AUDITED'}
                              onChange={() => toggleBulk(r.id)}
                            />
                          </td>
                          <td>
                            <div className="row-cat">{r.category.replace('_', ' ')}</div>
                            <span className="row-source">{r.source}</span>
                          </td>
                          <td>
                            <span className={`scope-badge ${r.scope.toLowerCase()}`}>
                              {r.scope.replace('_', ' ')}
                            </span>
                          </td>
                          <td>
                            <div className="row-raw">{r.raw_val} <span className="raw-unit">{r.raw_unit}</span></div>
                          </td>
                          <td>
                            <div className="row-norm">{r.norm_val.toLocaleString(undefined, { maximumFractionDigits: 3 })} <span className="norm-unit">{r.norm_unit}</span></div>
                          </td>
                          <td>
                            <span className="row-date">{r.act_date}</span>
                          </td>
                          <td>
                            <span className={`status-badge ${r.status.toLowerCase()}`}>{r.status}</span>
                            {hasIssues && <span className="issue-indicator">!</span>}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </main>

        {sel && (
          <aside className="inspect-panel">
            <div className="glass-panel inspect-card">
              <div className="inspect-header">
                <h3>Record Inspector</h3>
                <span className={`status-badge ${sel.status.toLowerCase()}`}>{sel.status}</span>
              </div>

              <div className="inspect-section side-by-side">
                <div className="inspect-box raw-box">
                  <h4>Raw Activity Payload</h4>
                  {editMode ? (
                    <div className="edit-form">
                      <div className="field-group">
                        <label>Raw Quantity</label>
                        <input
                          type="number"
                          value={editVal}
                          onChange={(e) => setEditVal(e.target.value)}
                        />
                      </div>
                      <div className="field-group">
                        <label>Raw Unit</label>
                        <input
                          type="text"
                          value={editUnit}
                          onChange={(e) => setEditUnit(e.target.value)}
                        />
                      </div>
                      <div className="edit-actions">
                        <button className="btn-success" onClick={() => handleEditSave(sel.id)}>Save</button>
                        <button className="btn-secondary" onClick={() => setEditMode(false)}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="data-row">
                        <span className="label">Activity Value:</span>
                        <span className="val highlight">{sel.raw_val} {sel.raw_unit}</span>
                      </div>
                      {sel.status !== 'AUDITED' && (
                        <button className="btn-small" onClick={() => setEditMode(true)}>Adjust Activity</button>
                      )}
                    </div>
                  )}
                </div>

                <div className="inspect-box norm-box">
                  <h4>Normalized Compliance State</h4>
                  <div className="data-row">
                    <span className="label">Scope:</span>
                    <span className="val">{sel.scope.replace('_', ' ')}</span>
                  </div>
                  <div className="data-row">
                    <span className="label">Category:</span>
                    <span className="val">{sel.category.replace('_', ' ')}</span>
                  </div>
                  <div className="data-row">
                    <span className="label">Normalized Value:</span>
                    <span className="val highlight">{sel.norm_val.toLocaleString(undefined, { maximumFractionDigits: 3 })} kgCO2e</span>
                  </div>
                  <div className="data-row">
                    <span className="label">Emission Factor:</span>
                    <span className="val">{sel.em_factor ? `${sel.em_factor} kgCO2e/unit` : 'N/A'}</span>
                  </div>
                  <div className="data-row">
                    <span className="label">Audit Status:</span>
                    <span className="val">{sel.status}</span>
                  </div>
                </div>
              </div>

              {sel.issues && sel.issues.length > 0 && (
                <div className="inspect-section panel-issues">
                  <h4>Validation Issues Ledger ({sel.issues.length})</h4>
                  <ul className="issue-list">
                    {sel.issues.map((i, idx) => (
                      <li key={idx} className={`issue-item ${i.severity.toLowerCase()}`}>
                        <div className="issue-meta">
                          <span className="issue-code">{i.code}</span>
                          <span className="issue-sev">{i.severity}</span>
                        </div>
                        <p className="issue-msg">{i.msg}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="inspect-section panel-audit">
                <h4>Audit Trail Ledgers</h4>
                {sel.audit && sel.audit.length > 0 ? (
                  <div className="timeline">
                    {sel.audit.map((a, idx) => (
                      <div key={idx} className="timeline-item">
                        <div className="timeline-dot"></div>
                        <div className="timeline-content">
                          <div className="timeline-meta">
                            <span className="action">{a.action}</span>
                            <span className="user">by {a.usr}</span>
                          </div>
                          <span className="time">{new Date(a.tstamp).toLocaleString()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-sub">No audit trail entries recorded yet.</div>
                )}
              </div>

              {sel.status !== 'AUDITED' && (
                <div className="inspect-actions">
                  <button className="btn-success" onClick={() => handleApprove(sel.id)}>Approve</button>
                  <button className="btn-warning" onClick={() => { setFlagCode('ANALYST_FLAG'); setFlagModal(true); }}>Flag Row</button>
                  <button className="btn-audit" onClick={() => handleLock(sel.id)}>Audit Lock</button>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>

      {flagModal && (
        <div className="modal-backdrop">
          <div className="glass-panel modal-card">
            <h3>Flag Row for Investigation</h3>
            <div className="field-group">
              <label>Reason Code</label>
              <select value={flagCode} onChange={(e) => setFlagCode(e.target.value)}>
                <option value="ANALYST_FLAG">Analyst Manual Check</option>
                <option value="SUSPICIOUS_SPIKE">Suspicious Activity Spike</option>
                <option value="MISSING_UNIT">Missing/Inaccurate Units</option>
                <option value="INVALID_VALUE">Invalid Value Representation</option>
              </select>
            </div>
            <div className="field-group">
              <label>Investigation Notes</label>
              <textarea
                value={flagMsg}
                onChange={(e) => setFlagMsg(e.target.value)}
                placeholder="Describe details for manual remediation..."
              />
            </div>
            <div className="modal-actions">
              <button className="btn-warning" onClick={() => handleFlag(sel.id)}>Submit Flag</button>
              <button className="btn-secondary" onClick={() => setFlagModal(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
