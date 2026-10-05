import React, { useState } from 'react';
import { User, Check, AlertCircle, Save } from 'lucide-react';
import type { PersonalInfo } from '../types/profile';
import { api } from '../services/api';

interface PersonalInfoSectionProps {
  personal: PersonalInfo;
  onUpdate: (updated: PersonalInfo) => void;
}

export const PersonalInfoSection: React.FC<PersonalInfoSectionProps> = ({ personal, onUpdate }) => {
  const [formData, setFormData] = useState<PersonalInfo>(personal);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const saved = await api.updatePersonal(formData);
      onUpdate(saved);
      setMessage({ type: 'success', text: 'Información personal guardada con éxito' });
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Error al guardar cambios' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 mb-8 transition-colors">
      <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-4 mb-6">
        <div className="flex items-center space-x-2.5">
          <User className="w-5 h-5 text-teal-600 dark:text-teal-400" />
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            Información Personal & Cabecera
          </h2>
        </div>
        {message && (
          <div
            className={`flex items-center space-x-1.5 text-xs px-3 py-1 rounded-md ${
              message.type === 'success'
                ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                : 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800'
            }`}
          >
            {message.type === 'success' ? <Check className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            <span>{message.text}</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="full_name" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Nombre Completo
            </label>
            <input
              id="full_name"
              type="text"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
            />
          </div>

          <div>
            <label htmlFor="headline" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Titular Profesional (Headline)
            </label>
            <input
              id="headline"
              type="text"
              name="headline"
              value={formData.headline}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Email (o variable de cabecera)
            </label>
            <input
              id="email"
              type="text"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
            />
          </div>

          <div>
            <label htmlFor="phone" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Teléfono (o variable de cabecera)
            </label>
            <input
              id="phone"
              type="text"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
            />
          </div>

          <div>
            <label htmlFor="github" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Usuario de GitHub
            </label>
            <input
              id="github"
              type="text"
              name="github"
              value={formData.github}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
            />
          </div>

          <div>
            <label htmlFor="linkedin" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Usuario de LinkedIn
            </label>
            <input
              id="linkedin"
              type="text"
              name="linkedin"
              value={formData.linkedin}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
            />
          </div>

          <div>
            <label htmlFor="location" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Ubicación
            </label>
            <input
              id="location"
              type="text"
              name="location"
              value={formData.location}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
            />
          </div>

          <div>
            <label htmlFor="timezone" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Zona Horaria
            </label>
            <input
              id="timezone"
              type="text"
              name="timezone"
              value={formData.timezone}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors"
            />
          </div>
        </div>

        <div>
          <label htmlFor="profile_summary" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
            Resumen Profesional (Executive Summary)
          </label>
          <textarea
            id="profile_summary"
            name="profile_summary"
            rows={3}
            value={formData.profile_summary}
            onChange={handleChange}
            className="w-full px-3 py-2 text-sm rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-teal-500 transition-colors resize-y"
          />
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium bg-teal-600 hover:bg-teal-700 dark:bg-teal-500 dark:hover:bg-teal-600 text-white transition-colors focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:outline-none disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Guardando...' : 'Guardar Información Personal'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
