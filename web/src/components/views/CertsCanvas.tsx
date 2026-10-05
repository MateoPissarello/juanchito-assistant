import React, { useState } from 'react';
import { Plus, Trash2, X } from 'lucide-react';
import type { Certification } from '../../types/profile';
import { api } from '../../services/api';

interface CertsCanvasProps {
  certifications: Certification[];
  onReload: () => void;
}

export const CertsCanvas: React.FC<CertsCanvasProps> = ({ certifications, onReload }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [form, setForm] = useState({
    issuer: '',
    title: '',
    issue_date: '',
  });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createCertification({
        issuer: form.issuer.trim(),
        title: form.title.trim(),
        issue_date: form.issue_date.trim(),
      });
      setShowAddForm(false);
      setForm({ issuer: '', title: '', issue_date: '' });
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al guardar certificación');
    }
  };

  const handleDelete = async (cert: Certification) => {
    if (!cert.id) return;
    if (!confirm(`¿Eliminar la certificación "${cert.title}"?`)) return;
    try {
      await api.deleteCertification(cert.id);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al eliminar');
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 sm:px-6">
      <div className="flex items-center justify-between pb-4 mb-6 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 font-mono tracking-tight">
            Professional Certifications ({certifications.length})
          </h1>
          <p className="text-xs text-zinc-500 font-mono mt-0.5">
            Credenciales de la industria verificadas para el Matcher
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowAddForm(!showAddForm)}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Credential</span>
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={handleCreate} className="border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 p-4 mb-6 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-100 dark:border-zinc-800">
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              New Certification
            </span>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-zinc-400 block mb-1">Issuer</label>
              <input
                type="text"
                required
                placeholder="Amazon Web Services (AWS)"
                value={form.issuer}
                onChange={(e) => setForm({ ...form, issuer: e.target.value })}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>
            <div>
              <label className="text-zinc-400 block mb-1">Title</label>
              <input
                type="text"
                required
                placeholder="AWS Certified Solutions Architect"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>
            <div>
              <label className="text-zinc-400 block mb-1">Date</label>
              <input
                type="text"
                required
                placeholder="Apr. 2025"
                value={form.issue_date}
                onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-2.5 py-1 rounded border border-zinc-200 dark:border-zinc-800 text-zinc-500"
            >
              cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-semibold"
            >
              save
            </button>
          </div>
        </form>
      )}

      {/* Certifications Table */}
      <div className="border border-zinc-200 dark:border-zinc-800 rounded overflow-hidden bg-white dark:bg-zinc-900/60 font-mono text-xs">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 text-zinc-500 uppercase tracking-wider text-[10px]">
              <th className="py-2.5 px-3">Issuer</th>
              <th className="py-2.5 px-3">Certification Title</th>
              <th className="py-2.5 px-3">Date</th>
              <th className="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/80">
            {certifications.map((cert) => (
              <tr key={cert.id} className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors">
                <td className="py-2.5 px-3 font-semibold text-zinc-900 dark:text-zinc-100">
                  {cert.issuer}
                </td>
                <td className="py-2.5 px-3 text-zinc-700 dark:text-zinc-300">
                  {cert.title}
                </td>
                <td className="py-2.5 px-3 text-zinc-500">
                  {cert.issue_date}
                </td>
                <td className="py-2.5 px-3 text-right">
                  <button
                    type="button"
                    onClick={() => handleDelete(cert)}
                    className="text-zinc-400 hover:text-rose-600 p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
