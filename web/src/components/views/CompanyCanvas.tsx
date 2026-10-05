import React, { useState } from 'react';
import {
  Plus,
  Trash2,
  Edit2,
  X,
  Layers,
} from 'lucide-react';
import type { WorkExperience, WorkProject } from '../../types/profile';
import { api } from '../../services/api';

interface CompanyCanvasProps {
  experience: WorkExperience;
  onReload: () => void;
  onDeleteCompany: (id: number) => void;
}

export const CompanyCanvas: React.FC<CompanyCanvasProps> = ({
  experience,
  onReload,
  onDeleteCompany,
}) => {
  const [editingCompany, setEditingCompany] = useState(false);
  const [companyForm, setCompanyForm] = useState({
    company: experience.company,
    role: experience.role,
    location: experience.location,
    start_date: experience.start_date,
    end_date: experience.end_date,
    is_current: experience.is_current,
  });

  // Adding initiative inline
  const [isAddingProject, setIsAddingProject] = useState(false);
  const [newProjectForm, setNewProjectForm] = useState({
    name: '',
    technologies: '',
    bullets: '',
    priority_weight: 1,
  });

  // Editing existing initiative
  const [editingProjectId, setEditingProjectId] = useState<number | null>(null);
  const [editingProjectForm, setEditingProjectForm] = useState({
    name: '',
    technologies: '',
    bullets: '',
    priority_weight: 1,
  });

  const handleUpdateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!experience.id) return;
    try {
      await api.updateExperience(experience.id, companyForm);
      setEditingCompany(false);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al actualizar empresa');
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!experience.id) return;

    const techArray = newProjectForm.technologies
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    const bulletArray = newProjectForm.bullets
      .split('\n')
      .map((b) => b.trim().replace(/^[-*•]\s*/, ''))
      .filter(Boolean);

    try {
      await api.createProject({
        work_experience_id: experience.id,
        name: newProjectForm.name.trim(),
        technologies: techArray,
        bullets: bulletArray,
        priority_weight: Number(newProjectForm.priority_weight),
      });
      setIsAddingProject(false);
      setNewProjectForm({ name: '', technologies: '', bullets: '', priority_weight: 1 });
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al crear iniciativa');
    }
  };

  const startEditProject = (proj: WorkProject) => {
    setEditingProjectId(proj.id || null);
    setEditingProjectForm({
      name: proj.name,
      technologies: proj.technologies.join(', '),
      bullets: proj.bullets.join('\n'),
      priority_weight: proj.priority_weight,
    });
  };

  const handleSaveEditProject = async (projId: number) => {
    const techArray = editingProjectForm.technologies
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    const bulletArray = editingProjectForm.bullets
      .split('\n')
      .map((b) => b.trim().replace(/^[-*•]\s*/, ''))
      .filter(Boolean);

    try {
      await api.updateProject(projId, {
        name: editingProjectForm.name.trim(),
        technologies: techArray,
        bullets: bulletArray,
        priority_weight: Number(editingProjectForm.priority_weight),
      });
      setEditingProjectId(null);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al guardar iniciativa');
    }
  };

  const handleDeleteProject = async (projId: number, name: string) => {
    if (!confirm(`¿Eliminar la iniciativa "${name}"?`)) return;
    try {
      await api.deleteProject(projId);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al eliminar');
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 sm:px-6">
      {/* Company Header Box */}
      <div className="border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900/60 p-5 mb-6">
        {!editingCompany ? (
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
                  {experience.company}
                </h1>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                  {experience.role}
                </span>
              </div>
              <div className="text-xs font-mono text-zinc-500 mt-1 flex items-center space-x-3">
                <span>{experience.start_date} — {experience.end_date}</span>
                <span>•</span>
                <span>{experience.location}</span>
              </div>
            </div>

            <div className="flex items-center space-x-2 text-xs font-mono">
              <button
                type="button"
                onClick={() => setEditingCompany(true)}
                className="p-1.5 rounded border border-zinc-200 dark:border-zinc-800 hover:border-zinc-400 dark:hover:border-zinc-600 text-zinc-600 dark:text-zinc-300"
                title="Editar información de la empresa"
              >
                <Edit2 className="w-3.5 h-3.5" />
              </button>

              <button
                type="button"
                onClick={() => experience.id && onDeleteCompany(experience.id)}
                className="p-1.5 rounded border border-zinc-200 dark:border-zinc-800 hover:border-rose-400 text-zinc-400 hover:text-rose-600"
                title="Eliminar empresa"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleUpdateCompany} className="space-y-3">
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div>
                <label className="text-zinc-400 block mb-1">Company</label>
                <input
                  type="text"
                  required
                  value={companyForm.company}
                  onChange={(e) => setCompanyForm({ ...companyForm, company: e.target.value })}
                  className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div>
                <label className="text-zinc-400 block mb-1">Role</label>
                <input
                  type="text"
                  required
                  value={companyForm.role}
                  onChange={(e) => setCompanyForm({ ...companyForm, role: e.target.value })}
                  className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div>
                <label className="text-zinc-400 block mb-1">Start Date</label>
                <input
                  type="text"
                  required
                  value={companyForm.start_date}
                  onChange={(e) => setCompanyForm({ ...companyForm, start_date: e.target.value })}
                  className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div>
                <label className="text-zinc-400 block mb-1">End Date</label>
                <input
                  type="text"
                  required
                  value={companyForm.end_date}
                  onChange={(e) => setCompanyForm({ ...companyForm, end_date: e.target.value })}
                  className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 text-xs font-mono">
              <button
                type="button"
                onClick={() => setEditingCompany(false)}
                className="px-2.5 py-1 rounded border border-zinc-200 dark:border-zinc-800 text-zinc-500"
              >
                cancel
              </button>
              <button
                type="submit"
                className="px-2.5 py-1 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-medium"
              >
                save
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Initiatives Section Header */}
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-zinc-400" />
          <h2 className="text-xs font-mono uppercase font-semibold text-zinc-700 dark:text-zinc-300 tracking-wider">
            Technical Initiatives ({experience.projects?.length || 0})
          </h2>
        </div>

        <button
          type="button"
          onClick={() => setIsAddingProject(!isAddingProject)}
          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded border border-zinc-200 dark:border-zinc-800 hover:border-zinc-400 dark:hover:border-zinc-600 text-xs font-mono text-zinc-700 dark:text-zinc-300 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Initiative</span>
        </button>
      </div>

      {/* Inline Initiative Creator */}
      {isAddingProject && (
        <form onSubmit={handleCreateProject} className="border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 p-4 mb-6 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-100 dark:border-zinc-800">
            <span className="text-xs font-mono font-semibold text-zinc-900 dark:text-zinc-100">
              New Initiative (WorkProject)
            </span>
            <button
              type="button"
              onClick={() => setIsAddingProject(false)}
              className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs font-mono">
            <div className="col-span-2">
              <label className="text-zinc-400 block mb-1">Initiative Name</label>
              <input
                type="text"
                required
                placeholder="Ej: AICodeFixer, Microservices EKS"
                value={newProjectForm.name}
                onChange={(e) => setNewProjectForm({ ...newProjectForm, name: e.target.value })}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>
            <div>
              <label className="text-zinc-400 block mb-1">Priority Weight</label>
              <input
                type="number"
                min="1"
                max="5"
                value={newProjectForm.priority_weight}
                onChange={(e) => setNewProjectForm({ ...newProjectForm, priority_weight: Number(e.target.value) })}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
            </div>
          </div>

          <div className="text-xs font-mono">
            <label className="text-zinc-400 block mb-1">Technologies (comma-separated)</label>
            <input
              type="text"
              placeholder="Python, AWS Bedrock, Docker, PostgreSQL"
              value={newProjectForm.technologies}
              onChange={(e) => setNewProjectForm({ ...newProjectForm, technologies: e.target.value })}
              className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
            />
          </div>

          <div className="text-xs font-mono">
            <div className="flex items-center justify-between mb-1">
              <label className="text-zinc-400">Impact Bullets (Google XYZ: Accomplished X measured by Y doing Z)</label>
              <span className="text-[10px] text-zinc-400">1 bullet per line • use **bold**</span>
            </div>
            <textarea
              rows={4}
              required
              placeholder="Designed automated analysis pipeline in **Python** reducing MTTR by **45%** on **AWS EKS**."
              value={newProjectForm.bullets}
              onChange={(e) => setNewProjectForm({ ...newProjectForm, bullets: e.target.value })}
              className="w-full p-2.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 leading-relaxed font-mono"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2 text-xs font-mono">
            <button
              type="button"
              onClick={() => setIsAddingProject(false)}
              className="px-2.5 py-1 rounded border border-zinc-200 dark:border-zinc-800 text-zinc-500"
            >
              cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-semibold"
            >
              save initiative
            </button>
          </div>
        </form>
      )}

      {/* Initiatives List */}
      <div className="space-y-4">
        {experience.projects && experience.projects.length > 0 ? (
          experience.projects.map((proj) => {
            const isEditing = editingProjectId === proj.id;
            return (
              <div
                key={proj.id}
                className="border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900/60 p-5 transition-colors"
              >
                {!isEditing ? (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2 font-mono">
                        <span className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                          {proj.name}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-700 text-zinc-500">
                          P{proj.priority_weight}
                        </span>
                      </div>

                      <div className="flex items-center space-x-1.5 text-xs font-mono text-zinc-400">
                        <button
                          type="button"
                          onClick={() => startEditProject(proj)}
                          className="p-1 hover:text-zinc-900 dark:hover:text-zinc-100"
                          title="Editar iniciativa"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => proj.id && handleDeleteProject(proj.id, proj.name)}
                          className="p-1 hover:text-rose-600"
                          title="Eliminar iniciativa"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Technologies Tags */}
                    {proj.technologies && proj.technologies.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 my-2.5">
                        {proj.technologies.map((t, i) => (
                          <span
                            key={i}
                            className="font-mono text-[11px] px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Google XYZ Bullets with Markdown preview */}
                    <ul className="space-y-1.5 mt-3 text-xs text-zinc-700 dark:text-zinc-300 list-disc list-inside font-sans">
                      {proj.bullets.map((b, idx) => (
                        <li key={idx} className="leading-relaxed">
                          <span
                            dangerouslySetInnerHTML={{
                              __html: b.replace(
                                /\*\*(.*?)\*\*/g,
                                '<strong class="font-semibold text-zinc-950 dark:text-zinc-100">$1</strong>'
                              ),
                            }}
                          />
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  /* Edit Initiative Form */
                  <div className="space-y-3">
                    <div className="grid grid-cols-3 gap-3 text-xs font-mono">
                      <div className="col-span-2">
                        <label className="text-zinc-400 block mb-1">Name</label>
                        <input
                          type="text"
                          value={editingProjectForm.name}
                          onChange={(e) => setEditingProjectForm({ ...editingProjectForm, name: e.target.value })}
                          className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-zinc-400 block mb-1">Priority</label>
                        <input
                          type="number"
                          min="1"
                          max="5"
                          value={editingProjectForm.priority_weight}
                          onChange={(e) => setEditingProjectForm({ ...editingProjectForm, priority_weight: Number(e.target.value) })}
                          className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 font-mono"
                        />
                      </div>
                    </div>

                    <div className="text-xs font-mono">
                      <label className="text-zinc-400 block mb-1">Technologies</label>
                      <input
                        type="text"
                        value={editingProjectForm.technologies}
                        onChange={(e) => setEditingProjectForm({ ...editingProjectForm, technologies: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 font-mono"
                      />
                    </div>

                    <div className="text-xs font-mono">
                      <label className="text-zinc-400 block mb-1">Impact Bullets</label>
                      <textarea
                        rows={4}
                        value={editingProjectForm.bullets}
                        onChange={(e) => setEditingProjectForm({ ...editingProjectForm, bullets: e.target.value })}
                        className="w-full p-2.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 leading-relaxed font-mono"
                      />
                    </div>

                    <div className="flex justify-end space-x-2 pt-1 text-xs font-mono">
                      <button
                        type="button"
                        onClick={() => setEditingProjectId(null)}
                        className="px-2.5 py-1 rounded border border-zinc-200 dark:border-zinc-800 text-zinc-500"
                      >
                        cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => proj.id && handleSaveEditProject(proj.id)}
                        className="px-3 py-1 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-semibold"
                      >
                        save changes
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="text-center py-10 border border-dashed border-zinc-200 dark:border-zinc-800 rounded font-mono text-xs text-zinc-400">
            Sin iniciativas técnicas en esta empresa. Haz clic en "Add Initiative" arriba.
          </div>
        )}
      </div>
    </div>
  );
};
