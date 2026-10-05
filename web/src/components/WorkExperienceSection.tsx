import React, { useState } from 'react';
import {
  Briefcase,
  Plus,
  Trash2,
  Edit2,
  ChevronDown,
  ChevronUp,
  FolderPlus,
  X,
} from 'lucide-react';
import type { WorkExperience, WorkProject } from '../types/profile';
import { api } from '../services/api';

interface WorkExperienceSectionProps {
  experiences: WorkExperience[];
  onReload: () => void;
}

export const WorkExperienceSection: React.FC<WorkExperienceSectionProps> = ({
  experiences,
  onReload,
}) => {
  const [expandedExps, setExpandedExps] = useState<Record<number, boolean>>(() => {
    const init: Record<number, boolean> = {};
    experiences.forEach((e) => {
      if (e.id) init[e.id] = true;
    });
    return init;
  });

  // Modal / Form state for Company
  const [showCompanyModal, setShowCompanyModal] = useState(false);
  const [editingCompany, setEditingCompany] = useState<WorkExperience | null>(null);
  const [companyForm, setCompanyForm] = useState({
    company: '',
    role: '',
    location: 'Bogotá, Colombia',
    start_date: '',
    end_date: 'Present',
    is_current: false,
    order_index: 0,
  });

  // Modal / Form state for Initiative (WorkProject)
  const [showProjModal, setShowProjModal] = useState(false);
  const [activeExpId, setActiveExpId] = useState<number | null>(null);
  const [editingProj, setEditingProj] = useState<WorkProject | null>(null);
  const [projForm, setProjForm] = useState({
    name: '',
    technologies: '',
    bullets: '',
    priority_weight: 1,
  });

  const toggleExp = (id: number) => {
    setExpandedExps((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // --- Handlers Empresa ---
  const openNewCompany = () => {
    setEditingCompany(null);
    setCompanyForm({
      company: '',
      role: '',
      location: 'Bogotá, Colombia',
      start_date: '',
      end_date: 'Present',
      is_current: false,
      order_index: experiences.length + 1,
    });
    setShowCompanyModal(true);
  };

  const openEditCompany = (exp: WorkExperience) => {
    setEditingCompany(exp);
    setCompanyForm({
      company: exp.company,
      role: exp.role,
      location: exp.location,
      start_date: exp.start_date,
      end_date: exp.end_date,
      is_current: exp.is_current,
      order_index: exp.order_index,
    });
    setShowCompanyModal(true);
  };

  const handleSaveCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingCompany && editingCompany.id) {
        await api.updateExperience(editingCompany.id, companyForm);
      } else {
        await api.createExperience(companyForm);
      }
      setShowCompanyModal(false);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al guardar empresa');
    }
  };

  const handleDeleteCompany = async (expId: number, companyName: string) => {
    if (!confirm(`¿Eliminar la empresa "${companyName}" y todas sus iniciativas técnicas?`)) return;
    try {
      await api.deleteExperience(expId);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al eliminar');
    }
  };

  // --- Handlers Iniciativa (WorkProject) ---
  const openNewProject = (expId: number) => {
    setActiveExpId(expId);
    setEditingProj(null);
    setProjForm({
      name: '',
      technologies: '',
      bullets: '',
      priority_weight: 1,
    });
    setShowProjModal(true);
  };

  const openEditProject = (proj: WorkProject) => {
    setActiveExpId(proj.work_experience_id);
    setEditingProj(proj);
    setProjForm({
      name: proj.name,
      technologies: proj.technologies.join(', '),
      bullets: proj.bullets.join('\n'),
      priority_weight: proj.priority_weight,
    });
    setShowProjModal(true);
  };

  const handleSaveProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeExpId) return;

    const techArray = projForm.technologies
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    const bulletArray = projForm.bullets
      .split('\n')
      .map((b) => b.trim().replace(/^[-*•]\s*/, ''))
      .filter(Boolean);

    try {
      if (editingProj && editingProj.id) {
        await api.updateProject(editingProj.id, {
          name: projForm.name,
          technologies: techArray,
          bullets: bulletArray,
          priority_weight: Number(projForm.priority_weight),
        });
      } else {
        await api.createProject({
          work_experience_id: activeExpId,
          name: projForm.name,
          technologies: techArray,
          bullets: bulletArray,
          priority_weight: Number(projForm.priority_weight),
        });
      }
      setShowProjModal(false);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al guardar iniciativa');
    }
  };

  const handleDeleteProject = async (projId: number, projName: string) => {
    if (!confirm(`¿Eliminar la iniciativa "${projName}"?`)) return;
    try {
      await api.deleteProject(projId);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al eliminar');
    }
  };

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 mb-8 transition-colors">
      <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-4 mb-6">
        <div className="flex items-center space-x-2.5">
          <Briefcase className="w-5 h-5 text-teal-600 dark:text-teal-400" />
          <div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              Experiencia Laboral e Iniciativas Técnicas
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Empresas y proyectos de ingeniería bajo la fórmula Google XYZ (resume.lol)
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={openNewCompany}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 transition-colors focus-visible:ring-2 focus-visible:ring-teal-500"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Agregar Empresa</span>
        </button>
      </div>

      {/* Lista de Empresas */}
      <div className="space-y-6">
        {experiences.length === 0 ? (
          <p className="text-sm text-zinc-500 text-center py-8">
            No hay experiencias registradas en la base de datos.
          </p>
        ) : (
          experiences.map((exp) => {
            const isExpanded = exp.id ? expandedExps[exp.id] ?? true : true;
            return (
              <div
                key={exp.id}
                className="border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden bg-zinc-50/50 dark:bg-zinc-950/40"
              >
                {/* Cabecera Empresa */}
                <div className="p-4 flex items-center justify-between bg-zinc-100/70 dark:bg-zinc-800/50 border-b border-zinc-200 dark:border-zinc-800">
                  <div className="flex items-center space-x-3">
                    <button
                      type="button"
                      onClick={() => exp.id && toggleExp(exp.id)}
                      className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 focus:outline-none"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-zinc-900 dark:text-zinc-100 text-sm">
                          {exp.role}
                        </span>
                        <span className="text-xs text-zinc-400">@</span>
                        <span className="font-medium text-teal-700 dark:text-teal-400 text-sm">
                          {exp.company}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-500 dark:text-zinc-400 flex items-center space-x-3 mt-0.5">
                        <span>{exp.start_date} – {exp.end_date}</span>
                        <span>•</span>
                        <span>{exp.location}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => exp.id && openNewProject(exp.id)}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-medium bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800 hover:bg-teal-100 transition-colors"
                      title="Agregar iniciativa a esta empresa"
                    >
                      <FolderPlus className="w-3.5 h-3.5" />
                      <span>Iniciativa</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => openEditCompany(exp)}
                      className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded"
                      title="Editar empresa"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => exp.id && handleDeleteCompany(exp.id, exp.company)}
                      className="p-1 text-zinc-400 hover:text-rose-600 rounded"
                      title="Eliminar empresa"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Sub-lista de Iniciativas Técnicas (WorkProject) */}
                {isExpanded && (
                  <div className="p-4 space-y-4">
                    {exp.projects && exp.projects.length > 0 ? (
                      exp.projects.map((proj) => (
                        <div
                          key={proj.id}
                          className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md p-4 shadow-xs"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-sm text-zinc-900 dark:text-zinc-100">
                                {proj.name}
                              </span>
                              <span className="text-xs px-2 py-0.5 rounded font-mono bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                                P{proj.priority_weight}
                              </span>
                            </div>

                            <div className="flex items-center space-x-1.5">
                              <button
                                type="button"
                                onClick={() => openEditProject(proj)}
                                className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded text-xs inline-flex items-center space-x-1"
                              >
                                <Edit2 className="w-3 h-3" />
                                <span>Editar</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => proj.id && handleDeleteProject(proj.id, proj.name)}
                                className="p-1 text-zinc-400 hover:text-rose-600 rounded"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </div>

                          {/* Technologies Chips */}
                          {proj.technologies && proj.technologies.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {proj.technologies.map((tech, i) => (
                                <span
                                  key={i}
                                  className="text-xs px-2 py-0.5 rounded font-mono bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-400 border border-teal-200/50 dark:border-teal-800/40"
                                >
                                  {tech}
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Viñetas Google XYZ */}
                          <ul className="space-y-1.5 text-xs text-zinc-700 dark:text-zinc-300 list-disc list-inside">
                            {proj.bullets.map((b, idx) => (
                              <li key={idx} className="leading-relaxed">
                                <span
                                  dangerouslySetInnerHTML={{
                                    __html: b.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-zinc-900 dark:text-zinc-100">$1</strong>'),
                                  }}
                                />
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-zinc-400 italic py-2">
                        Sin iniciativas registradas aún. Haz clic en "+ Iniciativa" para agregar una.
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Modal Empresa */}
      {showCompanyModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg max-w-md w-full p-6 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100 dark:border-zinc-800 mb-4">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-sm">
                {editingCompany ? 'Editar Empresa' : 'Nueva Empresa'}
              </h3>
              <button
                type="button"
                onClick={() => setShowCompanyModal(false)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveCompany} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Nombre de la Empresa
                </label>
                <input
                  type="text"
                  required
                  value={companyForm.company}
                  onChange={(e) => setCompanyForm({ ...companyForm, company: e.target.value })}
                  placeholder="Ej: Nubank, Blend360"
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Cargo / Rol
                </label>
                <input
                  type="text"
                  required
                  value={companyForm.role}
                  onChange={(e) => setCompanyForm({ ...companyForm, role: e.target.value })}
                  placeholder="Ej: Backend Engineer"
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    Fecha Inicio
                  </label>
                  <input
                    type="text"
                    required
                    value={companyForm.start_date}
                    onChange={(e) => setCompanyForm({ ...companyForm, start_date: e.target.value })}
                    placeholder="Nov. 2024"
                    className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    Fecha Fin
                  </label>
                  <input
                    type="text"
                    required
                    value={companyForm.end_date}
                    onChange={(e) => setCompanyForm({ ...companyForm, end_date: e.target.value })}
                    placeholder="Present"
                    className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Ubicación
                </label>
                <input
                  type="text"
                  value={companyForm.location}
                  onChange={(e) => setCompanyForm({ ...companyForm, location: e.target.value })}
                  placeholder="Bogotá, Colombia (Hybrid)"
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCompanyModal(false)}
                  className="px-3 py-1.5 text-xs rounded border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs rounded bg-teal-600 text-white font-medium hover:bg-teal-700"
                >
                  Guardar Empresa
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Iniciativa (WorkProject) */}
      {showProjModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg max-w-lg w-full p-6 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100 dark:border-zinc-800 mb-4">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-sm">
                {editingProj ? 'Editar Iniciativa Técnica' : 'Nueva Iniciativa Técnica'}
              </h3>
              <button
                type="button"
                onClick={() => setShowProjModal(false)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveProject} className="space-y-4">
              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    Nombre de la Iniciativa
                  </label>
                  <input
                    type="text"
                    required
                    value={projForm.name}
                    onChange={(e) => setProjForm({ ...projForm, name: e.target.value })}
                    placeholder="Ej: AICodeFixer, Microservices EKS"
                    className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    Prioridad (1-5)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={projForm.priority_weight}
                    onChange={(e) => setProjForm({ ...projForm, priority_weight: Number(e.target.value) })}
                    className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Tecnologías (separadas por coma)
                </label>
                <input
                  type="text"
                  value={projForm.technologies}
                  onChange={(e) => setProjForm({ ...projForm, technologies: e.target.value })}
                  placeholder="AWS Lambda, Python, PostgreSQL, Docker"
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    Viñetas de Impacto (1 por línea, usa **negrita** para métricas)
                  </label>
                  <span className="text-[10px] text-teal-600 dark:text-teal-400 font-mono">
                    Google XYZ Formula
                  </span>
                </div>
                <textarea
                  rows={4}
                  required
                  value={projForm.bullets}
                  onChange={(e) => setProjForm({ ...projForm, bullets: e.target.value })}
                  placeholder="Developed an automated pipeline in **Python** reducing latency by **45%** on **AWS EKS**."
                  className="w-full px-3 py-2 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono leading-relaxed"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowProjModal(false)}
                  className="px-3 py-1.5 text-xs rounded border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs rounded bg-teal-600 text-white font-medium hover:bg-teal-700"
                >
                  Guardar Iniciativa
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
