import React, { useState } from 'react';
import { Briefcase, ArrowLeft } from 'lucide-react';
import { api } from '../../services/api';

interface NewCompanyCanvasProps {
  onSuccess: (newExpId: number) => void;
  onCancel: () => void;
}

export const NewCompanyCanvas: React.FC<NewCompanyCanvasProps> = ({ onSuccess, onCancel }) => {
  const [form, setForm] = useState({
    company: '',
    role: '',
    location: 'Bogotá, Colombia',
    start_date: '',
    end_date: 'Present',
    is_current: false,
    order_index: 0,
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const created = await api.createExperience(form);
      if (created.id) {
        onSuccess(created.id);
      }
    } catch (err: any) {
      alert(err.message || 'Error al crear empresa');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <button
        type="button"
        onClick={onCancel}
        className="inline-flex items-center space-x-1.5 text-xs font-mono text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>back to explorer</span>
      </button>

      <div className="border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900/60 p-6">
        <div className="flex items-center space-x-2 pb-4 mb-4 border-b border-zinc-100 dark:border-zinc-800">
          <Briefcase className="w-4 h-4 text-zinc-400" />
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 font-mono">
            New Work Experience (Company)
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs font-mono">
          <div>
            <label className="text-zinc-400 block mb-1">Company Name</label>
            <input
              type="text"
              required
              placeholder="Nubank, Mercado Libre, Blend360"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              className="w-full px-3 py-2 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 font-sans text-sm font-semibold"
            />
          </div>

          <div>
            <label className="text-zinc-400 block mb-1">Role / Job Title</label>
            <input
              type="text"
              required
              placeholder="Backend Engineer, Trainee"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full px-3 py-1.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-zinc-400 block mb-1">Start Date</label>
              <input
                type="text"
                required
                placeholder="Nov. 2024"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                className="w-full px-3 py-1.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>
            <div>
              <label className="text-zinc-400 block mb-1">End Date</label>
              <input
                type="text"
                required
                placeholder="Present"
                value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                className="w-full px-3 py-1.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>
          </div>

          <div>
            <label className="text-zinc-400 block mb-1">Location</label>
            <input
              type="text"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="w-full px-3 py-1.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4 border-t border-zinc-100 dark:border-zinc-800">
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 rounded border border-zinc-200 dark:border-zinc-800 text-zinc-500"
            >
              cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-1.5 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-semibold disabled:opacity-50"
            >
              {loading ? 'creating...' : 'create company'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
