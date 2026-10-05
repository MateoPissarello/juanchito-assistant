import React, { useState } from 'react';
import { Save, Check, AlertCircle } from 'lucide-react';
import type { PersonalInfo } from '../../types/profile';
import { api } from '../../services/api';

interface PersonalHeaderCanvasProps {
  personal: PersonalInfo;
  onUpdate: (updated: PersonalInfo) => void;
}

export const PersonalHeaderCanvas: React.FC<PersonalHeaderCanvasProps> = ({ personal, onUpdate }) => {
  const [form, setForm] = useState<PersonalInfo>(personal);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatusMsg(null);
    try {
      const res = await api.updatePersonal(form);
      onUpdate(res);
      setStatusMsg({ type: 'ok', text: 'Variables de cabecera guardadas' });
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err: any) {
      setStatusMsg({ type: 'err', text: err.message || 'Error al guardar' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 sm:px-6">
      <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-4 mb-6">
        <div>
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 font-mono tracking-tight">
            Header & Variables (resume.lol)
          </h1>
          <p className="text-xs text-zinc-500 font-mono mt-0.5">
            Parametrización de variables dinámicas @NAME, @EMAIL, @PHONE y titular
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {statusMsg && (
            <span
              className={`text-xs font-mono inline-flex items-center space-x-1 ${
                statusMsg.type === 'ok' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600'
              }`}
            >
              {statusMsg.type === 'ok' ? <Check className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
              <span>{statusMsg.text}</span>
            </span>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? 'saving...' : 'save changes'}</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Document Header Preview / Inputs */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900/60 p-5 divide-y divide-zinc-100 dark:divide-zinc-800">
          <div className="pb-4">
            <label htmlFor="full_name" className="text-[11px] font-mono uppercase text-zinc-400 font-semibold block mb-1">
              Full Name (@NAME)
            </label>
            <input
              id="full_name"
              type="text"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              required
              className="w-full text-lg font-bold text-zinc-900 dark:text-zinc-100 bg-transparent border-0 border-b border-dashed border-zinc-300 dark:border-zinc-700 focus:border-zinc-900 dark:focus:border-zinc-100 focus:ring-0 p-0 pb-1"
            />
          </div>

          <div className="py-4">
            <label htmlFor="headline" className="text-[11px] font-mono uppercase text-zinc-400 font-semibold block mb-1">
              Professional Headline (&lt;div class=&quot;headline&quot;&gt;)
            </label>
            <input
              id="headline"
              type="text"
              name="headline"
              value={form.headline}
              onChange={handleChange}
              required
              className="w-full text-sm font-medium text-zinc-800 dark:text-zinc-200 bg-transparent border-0 border-b border-dashed border-zinc-300 dark:border-zinc-700 focus:border-zinc-900 dark:focus:border-zinc-100 focus:ring-0 p-0 pb-1 font-mono"
            />
          </div>

          <div className="pt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs font-mono">
            <div>
              <label htmlFor="email" className="text-[11px] text-zinc-400 block mb-1">@EMAIL</label>
              <input
                id="email"
                type="text"
                name="email"
                value={form.email}
                onChange={handleChange}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>

            <div>
              <label htmlFor="phone" className="text-[11px] text-zinc-400 block mb-1">@PHONE</label>
              <input
                id="phone"
                type="text"
                name="phone"
                value={form.phone}
                onChange={handleChange}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>

            <div>
              <label htmlFor="github" className="text-[11px] text-zinc-400 block mb-1">@GITHUB</label>
              <input
                id="github"
                type="text"
                name="github"
                value={form.github}
                onChange={handleChange}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>

            <div>
              <label htmlFor="linkedin" className="text-[11px] text-zinc-400 block mb-1">@LINKEDIN</label>
              <input
                id="linkedin"
                type="text"
                name="linkedin"
                value={form.linkedin}
                onChange={handleChange}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>

            <div>
              <label htmlFor="location" className="text-[11px] text-zinc-400 block mb-1">Location</label>
              <input
                id="location"
                type="text"
                name="location"
                value={form.location}
                onChange={handleChange}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>

            <div>
              <label htmlFor="timezone" className="text-[11px] text-zinc-400 block mb-1">Timezone</label>
              <input
                id="timezone"
                type="text"
                name="timezone"
                value={form.timezone}
                onChange={handleChange}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900/60 p-5">
          <label htmlFor="profile_summary" className="text-[11px] font-mono uppercase text-zinc-400 font-semibold block mb-2">
            Base Profile Summary (Markdown & Executive Background)
          </label>
          <textarea
            id="profile_summary"
            name="profile_summary"
            rows={4}
            value={form.profile_summary}
            onChange={handleChange}
            className="w-full text-xs font-mono leading-relaxed bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded p-3 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-zinc-400"
          />
        </div>
      </form>
    </div>
  );
};
