import React, { useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, SkeletonList, ViewHeader } from '../components/ui.jsx';

export function ExpensesView({ expenses, projects, loading, apiClient, onRefresh, showToast }) {
  const [busy, setBusy] = useState(false);
  const createExpense = async () => {
    const project = projects[0];
    if (!project) {
      showToast('Need a project to log an expense', 'error');
      return;
    }
    setBusy(true);
    try {
      await apiClient.createExpense({
        project_id: project.id,
        title: 'Desktop expense',
        amount: 0,
        expense_date: new Date().toISOString().slice(0, 10),
        category: 'general',
      });
      showToast('Expense created', 'success');
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
        subtitle="Track project expenses."
        action={
          <button className="btn primary" onClick={createExpense} disabled={busy}>
            New expense
          </button>
        }
      />
      {loading ? (
        <SkeletonList />
      ) : (
        <div className="list-card">
          {expenses?.length ? (
            expenses.map((item) => (
              <div className="list-row" key={item.id}>
                <strong>{item.title || item.category || `Expense ${item.id}`}</strong>
                <span>
                  {item.amount} · {item.expense_date || item.status}
                </span>
              </div>
            ))
          ) : (
            <EmptyState title="No expenses yet" text="Create one from a project." />
          )}
        </div>
      )}
    </div>
  );
}
