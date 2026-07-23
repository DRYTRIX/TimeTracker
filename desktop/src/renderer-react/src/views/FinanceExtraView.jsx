import React, { useEffect, useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, Panel, SkeletonList, ViewHeader } from '../components/ui.jsx';
import { listItems, todayISO } from '../utils/format.js';

export function FinanceExtraView({
  kind,
  title,
  subtitle,
  clients,
  projects,
  invoices,
  apiClient,
  showToast,
}) {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    amount: '',
    invoice_id: '',
    project_id: '',
    client_id: '',
    distance_km: '',
    description: '',
    title: '',
  });

  const load = async () => {
    setLoading(true);
    try {
      let res;
      if (kind === 'payments') res = await apiClient.getPayments({ per_page: 50 });
      else if (kind === 'mileage') res = await apiClient.getMileage({ per_page: 50 });
      else if (kind === 'quotes') res = await apiClient.getQuotes({ per_page: 50 });
      else if (kind === 'recurring') res = await apiClient.getRecurringInvoices({ per_page: 50 });
      else res = await apiClient.getCreditNotes({ per_page: 50 });
      setItems(listItems(res, kind === 'recurring' ? 'recurring_invoices' : kind, 'items'));
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [kind]);

  const create = async () => {
    setBusy(true);
    try {
      if (kind === 'payments') {
        await apiClient.createPayment({
          amount: Number(form.amount || 0),
          invoice_id: form.invoice_id ? Number(form.invoice_id) : undefined,
          payment_date: todayISO(),
        });
      } else if (kind === 'mileage') {
        await apiClient.createMileage({
          project_id: form.project_id ? Number(form.project_id) : projects[0]?.id,
          distance_km: Number(form.distance_km || 0),
          rate_per_km: Number(form.rate_per_km || 0.4),
          purpose: form.description || 'Desktop trip',
          start_location: form.start_location || 'Start',
          end_location: form.end_location || 'End',
          description: form.description || 'Desktop mileage',
          trip_date: todayISO(),
        });
      } else if (kind === 'quotes') {
        await apiClient.createQuote({
          client_id: form.client_id ? Number(form.client_id) : clients[0]?.id,
          project_id: form.project_id ? Number(form.project_id) : projects[0]?.id,
          title: form.title || 'Desktop quote',
        });
      } else if (kind === 'credit') {
        if (!form.invoice_id) {
          showToast('Select an invoice for the credit note', 'error');
          setBusy(false);
          return;
        }
        await apiClient.createCreditNote({
          invoice_id: Number(form.invoice_id),
          amount: Number(form.amount || 0),
          reason: form.description || 'Desktop credit note',
        });
      }
      showToast('Created', 'success');
      await load();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const generateRecurring = async (id) => {
    try {
      await apiClient.generateRecurringInvoice(id);
      showToast('Invoice generated', 'success');
      await load();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const openDetail = async (item) => {
    try {
      if (kind === 'quotes') {
        const res = await apiClient.getQuote(item.id);
        setSelected(res.quote || res);
      } else if (kind === 'credit') {
        const res = await apiClient.getCreditNote(item.id);
        setSelected(res.credit_note || res);
      } else {
        setSelected(item);
      }
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const labelFor = (item) => {
    if (kind === 'payments') return `Payment ${item.id} · ${item.amount}`;
    if (kind === 'mileage') return `${item.description || 'Trip'} · ${item.distance_km ?? item.distance} km`;
    if (kind === 'quotes') return item.quote_number || item.title || `Quote ${item.id}`;
    if (kind === 'recurring') return item.name || item.title || `Recurring ${item.id}`;
    return item.credit_note_number || `Credit note ${item.id}`;
  };

  return (
    <div className="view-stack split-view">
      <ViewHeader
        title={title}
        subtitle={subtitle}
        action={
          kind !== 'recurring' ? (
            <button className="btn primary" onClick={create} disabled={busy}>
              New
            </button>
          ) : (
            <button className="btn small" onClick={load}>
              Refresh
            </button>
          )
        }
      />
      {kind !== 'recurring' && (
        <Panel title="Quick create">
          <div className="form-grid report-filters">
            {(kind === 'payments' || kind === 'credit') && (
              <input
                type="number"
                placeholder="Amount"
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
              />
            )}
            {(kind === 'payments' || kind === 'credit') && (
              <select value={form.invoice_id} onChange={(e) => setForm((f) => ({ ...f, invoice_id: e.target.value }))}>
                <option value="">Invoice</option>
                {(invoices || []).map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.invoice_number || inv.id}
                  </option>
                ))}
              </select>
            )}
            {kind === 'mileage' && (
              <>
                <input
                  type="number"
                  placeholder="Distance km"
                  value={form.distance_km}
                  onChange={(e) => setForm((f) => ({ ...f, distance_km: e.target.value }))}
                />
                <input
                  placeholder="Description"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                />
                <select value={form.project_id} onChange={(e) => setForm((f) => ({ ...f, project_id: e.target.value }))}>
                  <option value="">Project</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </>
            )}
            {(kind === 'quotes' || kind === 'credit') && (
              <select value={form.client_id} onChange={(e) => setForm((f) => ({ ...f, client_id: e.target.value }))}>
                <option value="">Client</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            )}
            {kind === 'quotes' && (
              <input
                placeholder="Title"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              />
            )}
          </div>
        </Panel>
      )}
      {loading ? (
        <SkeletonList />
      ) : (
        <div className="split-panels">
          <div className="list-card">
            {items.length ? (
              items.map((item) => (
                <button
                  type="button"
                  className={`list-row buttonish ${selected?.id === item.id ? 'active' : ''}`}
                  key={item.id}
                  onClick={() => openDetail(item)}
                >
                  <strong>{labelFor(item)}</strong>
                  <span>{item.status || item.frequency || ''}</span>
                </button>
              ))
            ) : (
              <EmptyState title={`No ${title.toLowerCase()} yet`} text="Create one or enable the module on the server." />
            )}
          </div>
          <Panel title="Details">
            {!selected ? (
              <EmptyState title="Select a row" text="Choose an item for details." />
            ) : (
              <div className="form-grid">
                <pre className="detail-pre">{JSON.stringify(selected, null, 2)}</pre>
                {kind === 'recurring' && (
                  <button className="btn primary" onClick={() => generateRecurring(selected.id)}>
                    Generate now
                  </button>
                )}
              </div>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
