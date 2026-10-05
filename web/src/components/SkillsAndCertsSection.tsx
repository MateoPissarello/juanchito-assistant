import React, { useState } from 'react';
import { Database, Award, Plus, Trash2, X } from 'lucide-react';
import type { Certification, SkillCategory } from '../types/profile';
import { api } from '../services/api';

interface SkillsAndCertsSectionProps {
  skills: SkillCategory[];
  certifications: Certification[];
  onReload: () => void;
}

export const SkillsAndCertsSection: React.FC<SkillsAndCertsSectionProps> = ({
  skills,
  certifications,
  onReload,
}) => {
  const [newSkillInput, setNewSkillInput] = useState<Record<number, string>>({});
  const [showCertModal, setShowCertModal] = useState(false);
  const [certForm, setCertForm] = useState({
    issuer: '',
    title: '',
    issue_date: '',
  });

  const handleAddSkill = async (cat: SkillCategory) => {
    if (!cat.id) return;
    const skillName = (newSkillInput[cat.id] || '').trim();
    if (!skillName) return;

    if (cat.skills.includes(skillName)) {
      alert('Esta habilidad ya existe en la categoría');
      return;
    }

    try {
      const updatedSkills = [...cat.skills, skillName];
      await api.updateSkillCategory(cat.id, updatedSkills);
      setNewSkillInput((prev) => ({ ...prev, [cat.id!]: '' }));
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al agregar habilidad');
    }
  };

  const handleRemoveSkill = async (cat: SkillCategory, skillToRemove: string) => {
    if (!cat.id) return;
    try {
      const updatedSkills = cat.skills.filter((s) => s !== skillToRemove);
      await api.updateSkillCategory(cat.id, updatedSkills);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al remover habilidad');
    }
  };

  const handleAddCert = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createCertification({
        issuer: certForm.issuer.trim(),
        title: certForm.title.trim(),
        issue_date: certForm.issue_date.trim(),
      });
      setShowCertModal(false);
      setCertForm({ issuer: '', title: '', issue_date: '' });
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al crear certificación');
    }
  };

  const handleDeleteCert = async (cert: Certification) => {
    if (!cert.id) return;
    if (!confirm(`¿Eliminar la certificación "${cert.title}"?`)) return;
    try {
      await api.deleteCertification(cert.id);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al eliminar certificación');
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
      {/* Columna 1: Skills por Categoría */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 transition-colors">
        <div className="flex items-center space-x-2.5 border-b border-zinc-100 dark:border-zinc-800 pb-4 mb-6">
          <Database className="w-5 h-5 text-teal-600 dark:text-teal-400" />
          <div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              Habilidades Técnicas
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Categorizadas para optimizar el ATS Keyword Matcher
            </p>
          </div>
        </div>

        <div className="space-y-5">
          {skills.map((cat) => (
            <div key={cat.id || cat.category} className="space-y-2">
              <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 font-mono uppercase tracking-wider">
                {cat.category}
              </span>

              {/* Chips */}
              <div className="flex flex-wrap gap-1.5">
                {cat.skills.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 group hover:border-zinc-400 dark:hover:border-zinc-500 transition-colors"
                  >
                    <span>{skill}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(cat, skill)}
                      className="text-zinc-400 hover:text-rose-500 dark:hover:text-rose-400 p-0.5 rounded"
                      title={`Eliminar ${skill}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>

              {/* Input para agregar skill */}
              {cat.id && (
                <div className="flex items-center space-x-2 pt-1">
                  <input
                    type="text"
                    placeholder={`+ Agregar a ${cat.category}...`}
                    value={newSkillInput[cat.id] || ''}
                    onChange={(e) =>
                      setNewSkillInput({ ...newSkillInput, [cat.id!]: e.target.value })
                    }
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddSkill(cat);
                      }
                    }}
                    className="px-2.5 py-1 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                  <button
                    type="button"
                    onClick={() => handleAddSkill(cat)}
                    className="px-2 py-1 text-xs rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-teal-50 dark:hover:bg-teal-950/40 hover:text-teal-600 transition-colors"
                  >
                    Agregar
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Columna 2: Certificaciones Profesionales */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 transition-colors">
        <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-4 mb-6">
          <div className="flex items-center space-x-2.5">
            <Award className="w-5 h-5 text-teal-600 dark:text-teal-400" />
            <div>
              <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                Certificaciones
              </h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Credenciales reconocidas por el Matcher
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowCertModal(true)}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 transition-colors focus-visible:ring-2 focus-visible:ring-teal-500"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Agregar Cert</span>
          </button>
        </div>

        {/* Lista de Certificaciones */}
        <div className="space-y-3">
          {certifications.map((cert) => (
            <div
              key={cert.id}
              className="flex items-center justify-between p-3 rounded-md border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40"
            >
              <div>
                <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                  {cert.title}
                </p>
                <div className="flex items-center space-x-2 text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                  <span className="font-medium text-teal-700 dark:text-teal-400">
                    {cert.issuer}
                  </span>
                  <span>•</span>
                  <span>{cert.issue_date}</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleDeleteCert(cert)}
                className="text-zinc-400 hover:text-rose-600 p-1 rounded"
                title="Eliminar certificación"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Modal Agregar Certificación */}
      {showCertModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg max-w-md w-full p-6 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100 dark:border-zinc-800 mb-4">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-sm">
                Nueva Certificación Profesional
              </h3>
              <button
                type="button"
                onClick={() => setShowCertModal(false)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddCert} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Emisor (Issuer)
                </label>
                <input
                  type="text"
                  required
                  value={certForm.issuer}
                  onChange={(e) => setCertForm({ ...certForm, issuer: e.target.value })}
                  placeholder="Ej: Amazon Web Services (AWS), Oracle"
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Nombre de la Certificación (Título)
                </label>
                <input
                  type="text"
                  required
                  value={certForm.title}
                  onChange={(e) => setCertForm({ ...certForm, title: e.target.value })}
                  placeholder="Ej: AWS Certified Solutions Architect - Associate"
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Fecha de Emisión
                </label>
                <input
                  type="text"
                  required
                  value={certForm.issue_date}
                  onChange={(e) => setCertForm({ ...certForm, issue_date: e.target.value })}
                  placeholder="Ej: Apr. 2025"
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCertModal(false)}
                  className="px-3 py-1.5 text-xs rounded border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs rounded bg-teal-600 text-white font-medium hover:bg-teal-700"
                >
                  Guardar Certificación
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
