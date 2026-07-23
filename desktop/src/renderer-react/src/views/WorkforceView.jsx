import React from 'react';
import { classifyAxiosError } from '../services/api.js';
import { Panel, SkeletonGrid, StatCard, ViewHeader } from '../components/ui.jsx';

export function WorkforceView({
  workforce,
  user,
  invoiceApprovals,
  timeEntryApprovals,
  loading,
  apiClient,
  onRefresh,
  showToast,
}) {
  const periods = workforce?.periods?.timesheet_periods || workforce?.periods?.periods || workforce?.periods?.items || [];
  const requests = workforce?.requests?.time_off_requests || workforce?.requests?.requests || workforce?.requests?.items || [];
  const isAdmin = user?.is_admin;
  const canApprove = isAdmin || ['admin', 'owner', 'manager', 'approver'].includes(String(user?.role || '').toLowerCase());

  const act = async (fn, success) => {
    try {
      await fn();
      showToast(success, 'success');
      onRefresh();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  return (
    <div className="view-stack">
      <ViewHeader
        title="Workforce"
        subtitle="Timesheets, approvals, and leave."
        action={
          <button className="btn small" onClick={onRefresh}>
            Refresh
          </button>
        }
      />
      {loading ? (
        <SkeletonGrid />
      ) : (
        <>
          {(invoiceApprovals.length > 0 || timeEntryApprovals.length > 0) && canApprove && (
            <Panel title="Approvals inbox">
              {invoiceApprovals.map((a) => (
                <div className="list-row" key={`inv-${a.id}`}>
                  <span>Invoice {a.invoice_number || a.invoice_id}</span>
                  <div className="button-row">
                    <button className="btn small" onClick={() => act(() => apiClient.approveInvoiceApproval(a.id), 'Approved')}>
                      Approve
                    </button>
                    <button
                      className="btn small danger"
                      onClick={() => act(() => apiClient.rejectInvoiceApproval(a.id, 'Rejected'), 'Rejected')}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
              {timeEntryApprovals.map((a) => (
                <div className="list-row" key={`te-${a.id}`}>
                  <span>Time entry #{a.time_entry_id}</span>
                  <div className="button-row">
                    <button className="btn small" onClick={() => act(() => apiClient.approveTimeEntryApproval(a.id), 'Approved')}>
                      Approve
                    </button>
                    <button
                      className="btn small danger"
                      onClick={() => act(() => apiClient.rejectTimeEntryApproval(a.id, 'Rejected'), 'Rejected')}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </Panel>
          )}
          <div className="stats-grid">
            <StatCard label="Timesheet periods" value={periods.length} />
            <StatCard label="Time-off requests" value={requests.length} />
            <StatCard label="Capacity rows" value={(workforce?.capacity?.capacity || workforce?.capacity?.items || []).length} />
          </div>
          <Panel title="Timesheet periods">
            {periods.map((period) => (
              <div className="list-row" key={period.id}>
                <span>
                  {period.period_start} – {period.period_end} ({period.status})
                </span>
                <div className="button-row">
                  {period.status === 'draft' && (
                    <button className="btn small" onClick={() => act(() => apiClient.submitTimesheetPeriod(period.id), 'Submitted')}>
                      Submit
                    </button>
                  )}
                  {canApprove && period.status === 'submitted' && (
                    <>
                      <button className="btn small" onClick={() => act(() => apiClient.approveTimesheetPeriod(period.id), 'Approved')}>
                        Approve
                      </button>
                      <button
                        className="btn small danger"
                        onClick={() => act(() => apiClient.rejectTimesheetPeriod(period.id, 'Rejected'), 'Rejected')}
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {isAdmin && period.status === 'approved' && (
                    <button className="btn small" onClick={() => act(() => apiClient.closeTimesheetPeriod(period.id), 'Closed')}>
                      Close
                    </button>
                  )}
                </div>
              </div>
            ))}
          </Panel>
          <Panel title="Time-off requests">
            {requests.map((req) => (
              <div className="list-row" key={req.id}>
                <span>
                  {req.leave_type_name || 'Leave'} · {req.status}
                </span>
                {canApprove && req.status === 'submitted' && (
                  <div className="button-row">
                    <button className="btn small" onClick={() => act(() => apiClient.approveTimeOffRequest(req.id), 'Approved')}>
                      Approve
                    </button>
                    <button className="btn small danger" onClick={() => act(() => apiClient.rejectTimeOffRequest(req.id), 'Rejected')}>
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </Panel>
        </>
      )}
    </div>
  );
}
