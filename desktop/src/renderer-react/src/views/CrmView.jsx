import React, { useEffect, useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, Panel, SkeletonList, ViewHeader } from '../components/ui.jsx';
import { listItems } from '../utils/format.js';
import { t } from '../i18n/i18n.js';

const LEAD_STATUSES = ['new', 'contacted', 'qualified', 'converted', 'lost'];
const DEAL_STAGES = ['lead', 'qualified', 'proposal', 'negotiation', 'won', 'lost'];

export function CrmView({ clients, apiClient, showToast }) {
  const [tab, setTab] = useState('leads');
  const [leads, setLeads] = useState([]);
  const [deals, setDeals] = useState([]);
  const [selectedClientId, setSelectedClientId] = useState('');
  const [selectedLeadId, setSelectedLeadId] = useState(null);
  const [selectedDealId, setSelectedDealId] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    company_name: '',
    name: '',
    value: '',
    content: '',
    status: 'new',
    stage: 'lead',
  });

  const selectedLead = leads.find((l) => l.id === selectedLeadId) || null;
  const selectedDeal = deals.find((d) => d.id === selectedDealId) || null;

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

  useEffect(() => {
    if (selectedLead) {
      setForm((f) => ({
        ...f,
        first_name: selectedLead.first_name || '',
        last_name: selectedLead.last_name || '',
        email: selectedLead.email || '',
        company_name: selectedLead.company_name || '',
        status: selectedLead.status || 'new',
      }));
    }
  }, [selectedLeadId]);

  useEffect(() => {
    if (selectedDeal) {
      setForm((f) => ({
        ...f,
        name: selectedDeal.name || '',
        value: selectedDeal.value != null ? String(selectedDeal.value) : '',
        stage: selectedDeal.stage || selectedDeal.status || 'lead',
      }));
    }
  }, [selectedDealId]);

  const createLead = async () => {
    const firstName = form.first_name.trim();
    const lastName = form.last_name.trim();
    if (!firstName || !lastName) {
      showToast('First and last name are required', 'error');
      return;
    }
    try {
      await apiClient.createLead({
        first_name: firstName,
        last_name: lastName,
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

  const saveLead = async () => {
    if (!selectedLeadId) return;
    try {
      await apiClient.updateLead(selectedLeadId, {
        first_name: form.first_name.trim() || undefined,
        last_name: form.last_name.trim() || undefined,
        email: form.email || undefined,
        company_name: form.company_name || undefined,
        status: form.status || undefined,
      });
      showToast('Lead updated', 'success');
      await loadLeadsDeals();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const convertLead = async (toDeal) => {
    if (!selectedLeadId) return;
    try {
      if (toDeal) {
        await apiClient.convertLeadToDeal(selectedLeadId);
        showToast('Converted to deal', 'success');
      } else {
        await apiClient.convertLeadToClient(selectedLeadId);
        showToast('Converted to client', 'success');
      }
      setSelectedLeadId(null);
      await loadLeadsDeals();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const createDeal = async () => {
    const name = form.name.trim() || 'New deal';
    try {
      await apiClient.createDeal({
        name,
        value: form.value ? Number(form.value) : undefined,
        client_id: selectedClientId ? Number(selectedClientId) : undefined,
      });
      showToast('Deal created', 'success');
      setForm((f) => ({ ...f, name: '', value: '' }));
      await loadLeadsDeals();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const saveDeal = async () => {
    if (!selectedDealId) return;
    try {
      await apiClient.updateDeal(selectedDealId, {
        name: form.name.trim() || undefined,
        value: form.value !== '' ? Number(form.value) : undefined,
        stage: form.stage || undefined,
      });
      showToast('Deal updated', 'success');
      await loadLeadsDeals();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const createContact = async () => {
    if (!selectedClientId) return;
    const firstName = form.first_name.trim();
    const lastName = form.last_name.trim();
    if (!firstName || !lastName) {
      showToast('First and last name are required', 'error');
      return;
    }
    try {
      await apiClient.createContact(selectedClientId, {
        first_name: firstName,
        last_name: lastName,
        email: form.email || undefined,
      });
      showToast('Contact created', 'success');
      setForm((f) => ({ ...f, first_name: '', last_name: '', email: '' }));
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

  const tabs = [
    { id: 'leads', label: t('crm.leads', 'Leads') },
    { id: 'deals', label: t('crm.deals', 'Deals') },
    { id: 'clients', label: t('crm.clients', 'Clients') },
  ];

  return (
    <div className="view-stack">
      <ViewHeader title={t('crm.title', 'CRM')} subtitle={t('crm.subtitle', 'Leads, deals, contacts, and client notes.')} />
      <div className="tab-row">
        {tabs.map((item) => (
          <button
            key={item.id}
            className={`btn small ${tab === item.id ? 'primary' : 'ghost'}`}
            onClick={() => setTab(item.id)}
          >
            {item.label}
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
              <button
                type="button"
                className={`list-row ${selectedLeadId === lead.id ? 'selected' : ''}`}
                key={lead.id}
                onClick={() => setSelectedLeadId(lead.id)}
              >
                <strong>{[lead.first_name, lead.last_name].filter(Boolean).join(' ') || lead.company_name || `Lead ${lead.id}`}</strong>
                <span>{lead.status} · {lead.email || '—'}</span>
              </button>
            )) : <EmptyState title="No leads" text="Create a lead or enable the CRM module." />}
          </div>
          {selectedLead && (
            <Panel title={t('crm.editLead', 'Edit lead')}>
              <div className="form-grid report-filters">
                <input placeholder="First name" value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} />
                <input placeholder="Last name" value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} />
                <input placeholder="Email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
                <input placeholder="Company" value={form.company_name} onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))} />
                <label>
                  {t('crm.status', 'Status')}
                  <select value={form.status} onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}>
                    {LEAD_STATUSES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <button className="btn primary" onClick={saveLead}>{t('crm.saveChanges', 'Save changes')}</button>
                <button className="btn ghost" onClick={() => convertLead(false)}>{t('crm.convertToClient', 'Convert to client')}</button>
                <button className="btn ghost" onClick={() => convertLead(true)}>{t('crm.convertToDeal', 'Convert to deal')}</button>
              </div>
            </Panel>
          )}
        </>
      )}
      {!loading && tab === 'deals' && (
        <>
          <Panel title="New deal">
            <div className="form-grid report-filters">
              <input placeholder="Deal name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
              <input placeholder="Value" type="number" value={form.value} onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))} />
              <select value={selectedClientId} onChange={(e) => setSelectedClientId(e.target.value)}>
                <option value="">Client (optional)</option>
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <button className="btn primary" onClick={createDeal}>Create deal</button>
            </div>
          </Panel>
          <div className="list-card">
            {deals.length ? deals.map((deal) => (
              <button
                type="button"
                className={`list-row ${selectedDealId === deal.id ? 'selected' : ''}`}
                key={deal.id}
                onClick={() => setSelectedDealId(deal.id)}
              >
                <strong>{deal.name || `Deal ${deal.id}`}</strong>
                <span>{deal.stage || deal.status} · {deal.value != null ? deal.value : '—'}</span>
              </button>
            )) : <EmptyState title="No deals" text="Create a deal to get started." />}
          </div>
          {selectedDeal && (
            <Panel title={t('crm.editDeal', 'Edit deal')}>
              <div className="form-grid report-filters">
                <input placeholder="Deal name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
                <input placeholder="Value" type="number" value={form.value} onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))} />
                <label>
                  {t('crm.stage', 'Stage')}
                  <select value={form.stage} onChange={(e) => setForm((f) => ({ ...f, stage: e.target.value }))}>
                    {DEAL_STAGES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <button className="btn primary" onClick={saveDeal}>{t('crm.saveChanges', 'Save changes')}</button>
              </div>
            </Panel>
          )}
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
