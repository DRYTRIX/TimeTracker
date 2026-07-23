import React, { useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, Panel, SkeletonList, ViewHeader } from '../components/ui.jsx';

export function InvoicesView({ invoices, projects, clients, loading, apiClient, onRefresh, showToast }) {
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadDetail = async (id) => {
    setSelectedId(id);
    try {
      const res = await apiClient.getInvoice(id);
      setDetail(res.invoice || null);
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const createInvoice = async () => {
    const project = projects[0];
    const client = clients[0];
    if (!project || !client) {
      showToast('Need at least one project and client', 'error');
      return;
    }
    setBusy(true);
    try {
      const due = new Date();
      due.setDate(due.getDate() + 30);
      await apiClient.createInvoice({
        project_id: project.id,
        client_id: client.id,
        client_name: client.name,
        due_date: due.toISOString().slice(0, 10),
      });
      showToast('Invoice created', 'success');
      onRefresh();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const updateStatus = async (status, amountPaid) => {
    if (!selectedId) return;
    setBusy(true);
    try {
      const payload = { status };
      if (amountPaid != null) payload.amount_paid = amountPaid;
      await apiClient.updateInvoice(selectedId, payload);
      showToast('Invoice updated', 'success');
      await loadDetail(selectedId);
      onRefresh();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const downloadPdf = async () => {
    if (!selectedId || !detail) return;
    try {
      const buffer = await apiClient.downloadInvoicePdf(selectedId);
      const blob = new Blob([buffer], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${detail.invoice_number || 'invoice'}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  return (
    <div className="view-stack split-view">
      <ViewHeader
        title="Invoices"
        subtitle="Create, review, and update invoices."
        action={
          <button className="btn primary" onClick={createInvoice} disabled={busy}>
            New invoice
          </button>
        }
      />
      {loading ? (
        <SkeletonList />
      ) : (
        <div className="split-panels">
          <div className="list-card">
            {invoices?.length ? (
              invoices.map((item) => (
                <button
                  type="button"
                  className={`list-row buttonish ${selectedId === item.id ? 'active' : ''}`}
                  key={item.id}
                  onClick={() => loadDetail(item.id)}
                >
                  <strong>{item.invoice_number || `Invoice ${item.id}`}</strong>
                  <span>
                    {item.status} · {item.total_amount}
                  </span>
                </button>
              ))
            ) : (
              <EmptyState title="No invoices yet" text="Create one to get started." />
            )}
          </div>
          <Panel
            title={detail ? detail.invoice_number : 'Details'}
            action={detail && <button className="btn small" onClick={downloadPdf}>PDF</button>}
          >
            {!detail ? (
              <EmptyState title="Select an invoice" text="Choose a row to view line items." />
            ) : (
              <div className="form-grid">
                <p>
                  {detail.client_name} · {detail.status}
                </p>
                <p>Total: {detail.total_amount}</p>
                {(detail.items || []).map((item) => (
                  <div key={item.id} className="list-row">
                    <span>{item.description}</span>
                    <span>{item.total_amount}</span>
                  </div>
                ))}
                <div className="button-row">
                  {detail.status !== 'sent' && (
                    <button className="btn" onClick={() => updateStatus('sent')}>
                      Mark sent
                    </button>
                  )}
                  {detail.status !== 'paid' && (
                    <button className="btn" onClick={() => updateStatus('paid', detail.total_amount)}>
                      Mark paid
                    </button>
                  )}
                  <button className="btn ghost" onClick={onRefresh}>
                    Refresh list
                  </button>
                </div>
              </div>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
