import React, { useEffect, useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, Panel, SkeletonList, ViewHeader } from '../components/ui.jsx';
import { listItems } from '../utils/format.js';

export function CrmView({ clients, apiClient, showToast }) {
  const [tab, setTab] = useState('leads');
  const [leads, setLeads] = useState([]);
  const [deals, setDeals] = useState([]);
  const [selectedClientId, setSelectedClientId] = useState('');
  const [contacts, setContacts] = useState([]);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', company_name: '', name: '', amount: '', content: '' });

  const loadLeadsDeals = async () => {
    setLoading(true);
    try {
      const [leadsRes, dealsRes] = await Promise.all([
        apiClient.getLeads({ per_page: 50 }),
        apiClient.getDeals({ per_page: 50 }),
      ]);
      setLeads(listItems(leadsRes, 'leads'));
      setDeals(listItems(dealsRes, 'deals'));
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadClientExtras = async (clientId) => {
    if (!clientId) return;
    setLoading(true);
    try {
      const [cRes, nRes] = await Promise.all([
        apiClient.getContacts(clientId),
        apiClient.getClientNotes(clientId),
      ]);
      setContacts(listItems(cRes, 'contacts'));
      setNotes(listItems(nRes, 'notes', 'client_notes'));
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeadsDeals();
  }, []);

  useEffect(() => {
    if (!selectedClientId && clients[0]) setSelectedClientId(String(clients[0].id));
  }, [clients, selectedClientId]);

  useEffect(() => {
    if (tab === 'clients' && selectedClientId) loadClientExtras(selectedClientId);
  }, [tab, selectedClientId]);

  const createLead = async () => {
    try {
      await apiClient.createLead({
        first_name: form.first_name || 'Lead',
        last_name: form.last_name || '',
        email: form.email || undefined,
        company_name: form.company_name || undefined,
      });
      showToast('Lead created', 'success');
      setForm((f) => ({ ...f, first_name: '', last_name: '', email: '', company_name: '' }));
      await loadLeadsDeals();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const createDeal = async () => {
    try {
      await apiClient.createDeal({
        name: form.name || 'New deal',
        amount: form.amount ? Number(form.amount) : 0,
        client_id: selectedClientId ? Number(selectedClientId) : undefined,
      });
      showToast('Deal created', 'success');
      setForm((f) => ({ ...f, name: '', amount: '' }));
      await loadLeadsDeals();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const createContact = async () => {
    if (!selectedClientId) return;
    try {
      await apiClient.createContact(selectedClientId, {
        first_name: form.first_name || 'Contact',
        last_name: form.last_name || '',
        email: form.email || undefined,
      });
      showToast('Contact created', 'success');
      await loadClientExtras(selectedClientId);
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const createNote = async () => {
    if (!selectedClientId || !form.content.trim()) return;
    try {
      await apiClient.createClientNote(selectedClientId, { content: form.content.trim() });
      showToast('Note added', 'success');
      setForm((f) => ({ ...f, content: '' }));
      await loadClientExtras(selectedClientId);
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  return (
    <div className="view-stack">
      <ViewHeader title="CRM" subtitle="Leads, deals, contacts, and client notes." />
      <div className="tab-row">
        {['leads', 'deals', 'clients'].map((id) => (
          <button key={id} className={`btn small ${tab === id ? 'primary' : 'ghost'}`} onClick={() => setTab(id)}>
            {id[0].toUpperCase() + id.slice(1)}
          </button>
        ))}
      </div>
      {loading && <SkeletonList />}
      {!loading && tab === 'leads' && (
        <>
          <Panel title="New lead">
            <div className="form-grid report-filters">
              <input placeholder="First name" value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} />
              <input placeholder="Last name" value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} />
              <input placeholder="Email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
              <input placeholder="Company" value={form.company_name} onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))} />
              <button className="btn primary" onClick={createLead}>Create lead</button>
            </div>
          </Panel>
          <div className="list-card">
            {leads.length ? leads.map((lead) => (
              <div className="list-row" key={lead.id}>
                <strong>{[lead.first_name, lead.last_name].filter(Boolean).join(' ') || lead.company_name || `Lead ${lead.id}`}</strong>
                <span>{lead.status} · {lead.email || '—'}</span>
              </div>
            )) : <EmptyState title="No leads" text="Create a lead or enable the CRM module." />}
          </div>
        </>
      )}
      {!loading && tab === 'deals' && (
        <>
          <Panel title="New deal">
            <div className="form-grid report-filters">
              <input placeholder="Deal name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
              <input placeholder="Amount" type="number" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
              <select value={selectedClientId} onChange={(e) => setSelectedClientId(e.target.value)}>
                <option value="">Client (optional)</option>
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <button className="btn primary" onClick={createDeal}>Create deal</button>
            </div>
          </Panel>
          <div className="list-card">
            {deals.length ? deals.map((deal) => (
              <div className="list-row" key={deal.id}>
                <strong>{deal.name || `Deal ${deal.id}`}</strong>
                <span>{deal.stage || deal.status} · {deal.amount}</span>
              </div>
            )) : <EmptyState title="No deals" text="Create a deal to get started." />}
          </div>
        </>
      )}
      {!loading && tab === 'clients' && (
        <>
          <label>
            Client
            <select value={selectedClientId} onChange={(e) => setSelectedClientId(e.target.value)}>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <Panel title="Contacts">
            <div className="form-grid report-filters">
              <input placeholder="First name" value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} />
              <input placeholder="Last name" value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} />
              <input placeholder="Email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
              <button className="btn primary" onClick={createContact}>Add contact</button>
            </div>
            {contacts.map((c) => (
              <div className="list-row" key={c.id}>
                <strong>{[c.first_name, c.last_name].filter(Boolean).join(' ') || c.email}</strong>
                <span>{c.email || c.phone || '—'}</span>
              </div>
            ))}
            {!contacts.length && <EmptyState title="No contacts" text="Add a contact for this client." />}
          </Panel>
          <Panel title="Notes">
            <div className="form-grid">
              <textarea placeholder="Note content" value={form.content} onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))} />
              <button className="btn primary" onClick={createNote}>Add note</button>
            </div>
            {notes.map((n) => (
              <div className="list-row" key={n.id}>
                <span>{n.content || n.body || n.note}</span>
              </div>
            ))}
            {!notes.length && <EmptyState title="No notes" text="Add a client note." />}
          </Panel>
        </>
      )}
    </div>
  );
}
