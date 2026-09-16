import React, { useMemo, useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, SkeletonList, ViewHeader } from '../components/ui.jsx';

export function ExpensesView({ expenses, projects, loading, apiClient, onRefresh, showToast }) {
  const [busy, setBusy] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [draft, setDraft] = useState(null);

  const selected = useMemo(
    () => (expenses || []).find((e) => e.id === selectedId) || null,
    [expenses, selectedId],
  );

  const openCreate = () => {
    setSelectedId(null);
    setDraft({
      title: '',
      category: 'general',
      amount: '',
      expense_date: new Date().toISOString().slice(0, 10),
      project_id: projects?.[0]?.id || '',
      billable: false,
      reimbursable: true,
    });
  };

  const openEdit = (item) => {
    setSelectedId(item.id);
    setDraft({
      title: item.title || '',
      category: item.category || 'general',
      amount: String(item.amount ?? ''),
      expense_date: item.expense_date || new Date().toISOString().slice(0, 10),
      project_id: item.project_id || '',
      billable: !!item.billable,
      reimbursable: item.reimbursable !== false,
      status: item.status || 'pending',
    });
  };

  const saveExpense = async () => {
    if (!draft?.title || !draft?.category || !draft?.amount) {
      showToast('Title, category, and amount are required', 'error');
      return;
    }
    const amount = Number(draft.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      showToast('Enter a valid amount', 'error');
      return;
    }
    setBusy(true);
    try {
      const payload = {
        title: draft.title.trim(),
        category: draft.category.trim(),
        amount,
        expense_date: draft.expense_date,
        billable: !!draft.billable,
        reimbursable: !!draft.reimbursable,
        ...(draft.project_id ? { project_id: Number(draft.project_id) } : {}),
      };
      if (selectedId) {
        await apiClient.updateExpense(selectedId, payload);
        showToast('Expense updated', 'success');
      } else {
        await apiClient.createExpense(payload);
        showToast('Expense created', 'success');
      }
      setDraft(null);
      setSelectedId(null);
      onRefresh();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await apiClient.approveExpense(selectedId);
      showToast('Expense approved', 'success');
      onRefresh();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setBusy(false);
    }
  };

  const reject = async () => {
    if (!selectedId) return;
    const reason = window.prompt('Rejection reason');
    if (!reason) return;
    setBusy(true);
    try {
      await apiClient.rejectExpense(selectedId, reason);
      showToast('Expense rejected', 'success');
      onRefresh();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="view-stack">
      <ViewHeader
        title="Expenses"
        subtitle="Track, edit, and approve project expenses."
        action={
          <button className="btn primary" onClick={openCreate} disabled={busy}>
            New expense
          </button>
        }
      />
      {loading ? (
        <SkeletonList />
      ) : (
        <div className="split-panel" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="list-card">
            {expenses?.length ? (
              expenses.map((item) => (
                <button
                  type="button"
                  className="list-row"
                  key={item.id}
                  onClick={() => openEdit(item)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    background: selectedId === item.id ? 'var(--surface-2, #eee)' : 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <strong>{item.title || item.category || `Expense ${item.id}`}</strong>
                  <span>
                    {item.amount} · {item.expense_date || item.status}
                  </span>
                </button>
              ))
            ) : (
              <EmptyState title="No expenses yet" text="Create one to get started." />
            )}
          </div>

          <div className="list-card" style={{ padding: 16 }}>
            {!draft ? (
              <EmptyState title="Select an expense" text="Or create a new one." />
            ) : (
              <div style={{ display: 'grid', gap: 10 }}>
                <h3 style={{ margin: 0 }}>{selectedId ? 'Edit expense' : 'New expense'}</h3>
                <label>
                  Title
                  <input
                    value={draft.title}
                    onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                  />
                </label>
                <label>
                  Category
                  <input
                    value={draft.category}
                    onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                  />
                </label>
                <label>
                  Amount
                  <input
                    value={draft.amount}
                    onChange={(e) => setDraft({ ...draft, amount: e.target.value })}
                  />
                </label>
                <label>
                  Date
                  <input
                    type="date"
                    value={draft.expense_date}
                    onChange={(e) => setDraft({ ...draft, expense_date: e.target.value })}
                  />
                </label>
                <label>
                  Project
                  <select
                    value={draft.project_id}
                    onChange={(e) => setDraft({ ...draft, project_id: e.target.value })}
                  >
                    <option value="">None</option>
                    {(projects || []).map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={!!draft.billable}
                    onChange={(e) => setDraft({ ...draft, billable: e.target.checked })}
                  />{' '}
                  Billable
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={!!draft.reimbursable}
                    onChange={(e) => setDraft({ ...draft, reimbursable: e.target.checked })}
                  />{' '}
                  Reimbursable
                </label>
                {selected && <div>Status: {selected.status || 'pending'}</div>}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button className="btn primary" onClick={saveExpense} disabled={busy}>
                    Save
                  </button>
                  {selectedId && selected?.status === 'pending' && (
                    <>
                      <button className="btn" onClick={approve} disabled={busy}>
                        Approve
                      </button>
                      <button className="btn" onClick={reject} disabled={busy}>
                        Reject
                      </button>
                    </>
                  )}
                  <button
                    className="btn"
                    onClick={() => {
                      setDraft(null);
                      setSelectedId(null);
                    }}
                    disabled={busy}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
