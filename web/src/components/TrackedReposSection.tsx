import React, { useState } from 'react';
import { Terminal, Plus, Trash2, ExternalLink, GitBranch, Star, X } from 'lucide-react';
import type { TrackedRepo } from '../types/profile';
import { api } from '../services/api';

interface TrackedReposSectionProps {
  repos: TrackedRepo[];
  onReload: () => void;
  githubUser: string;
}

export const TrackedReposSection: React.FC<TrackedReposSectionProps> = ({
  repos,
  onReload,
  githubUser,
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRepo, setNewRepo] = useState({
    name: '',
    branch: '',
    category: 'Backend',
    priority: 1,
    notes: '',
  });

  const handleToggle = async (repo: TrackedRepo) => {
    if (!repo.id) return;
    try {
      await api.toggleRepo(repo.id);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al alternar estado');
    }
  };

  const handleDelete = async (repo: TrackedRepo) => {
    if (!repo.id) return;
    if (!confirm(`¿Remover "${repo.name}" de los repositorios seguidos en SQLite?`)) return;
    try {
      await api.deleteRepo(repo.id);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al eliminar');
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createRepo({
        name: newRepo.name.trim(),
        branch: newRepo.branch.trim() || null,
        category: newRepo.category.trim() || null,
        priority: Number(newRepo.priority),
        is_active: true,
        notes: newRepo.notes.trim() || null,
      });
      setShowAddModal(false);
      setNewRepo({ name: '', branch: '', category: 'Backend', priority: 1, notes: '' });
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al agregar repositorio');
    }
  };

  const activeCount = repos.filter((r) => r.is_active).length;

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 mb-8 transition-colors">
      <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-4 mb-6">
        <div className="flex items-center space-x-2.5">
          <Terminal className="w-5 h-5 text-teal-600 dark:text-teal-400" />
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                Repositorios de GitHub Seguidos
              </h2>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                {activeCount} de {repos.length} activos
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Administra los repositorios sincronizados por GitHubIngestService en SQLite
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 transition-colors focus-visible:ring-2 focus-visible:ring-teal-500"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Seguir Repositorio</span>
        </button>
      </div>

      {/* Grid de Repositorios */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {repos.map((repo) => (
          <div
            key={repo.id}
            className={`border rounded-lg p-4 transition-all ${
              repo.is_active
                ? 'border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-xs'
                : 'border-zinc-200 dark:border-zinc-800/60 bg-zinc-50/50 dark:bg-zinc-950/40 opacity-60'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center space-x-1.5">
                <a
                  href={`https://github.com/${githubUser}/${repo.name}`}
                  target="_blank"
                  rel="noreferrer"
                  className="font-mono text-sm font-semibold text-zinc-900 dark:text-zinc-100 hover:text-teal-600 dark:hover:text-teal-400 inline-flex items-center space-x-1"
                >
                  <span className="truncate max-w-[170px]">{repo.name}</span>
                  <ExternalLink className="w-3 h-3 text-zinc-400" />
                </a>
              </div>

              {/* Toggle Switch */}
              <button
                type="button"
                onClick={() => handleToggle(repo)}
                aria-label={repo.is_active ? `Desactivar ${repo.name}` : `Activar ${repo.name}`}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 ${
                  repo.is_active ? 'bg-teal-600 dark:bg-teal-500' : 'bg-zinc-300 dark:bg-zinc-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                    repo.is_active ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Badges: Category & Branch */}
            <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono my-2.5">
              {repo.category && (
                <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 text-[11px]">
                  {repo.category}
                </span>
              )}
              {repo.branch && (
                <span className="px-2 py-0.5 rounded bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-400 border border-teal-200/50 dark:border-teal-800/40 text-[11px] inline-flex items-center space-x-1">
                  <GitBranch className="w-3 h-3" />
                  <span>{repo.branch}</span>
                </span>
              )}
              <span className="px-1.5 py-0.5 rounded text-[11px] text-zinc-500 inline-flex items-center space-x-0.5">
                <Star className="w-3 h-3 text-amber-500" />
                <span>P{repo.priority}</span>
              </span>
            </div>

            {repo.notes && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400 italic truncate mb-2">
                {repo.notes}
              </p>
            )}

            <div className="flex justify-end pt-2 border-t border-zinc-100 dark:border-zinc-800">
              <button
                type="button"
                onClick={() => handleDelete(repo)}
                className="text-xs text-zinc-400 hover:text-rose-600 transition-colors p-1"
                title="Dejar de seguir repositorio"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal Agregar Repositorio */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg max-w-md w-full p-6 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100 dark:border-zinc-800 mb-4">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-sm">
                Seguir Nuevo Repositorio en SQLite
              </h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Nombre del Repositorio en GitHub
                </label>
                <input
                  type="text"
                  required
                  value={newRepo.name}
                  onChange={(e) => setNewRepo({ ...newRepo, name: e.target.value })}
                  placeholder="ej: my-awesome-backend"
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    Rama Específica (Opcional)
                  </label>
                  <input
                    type="text"
                    value={newRepo.branch}
                    onChange={(e) => setNewRepo({ ...newRepo, branch: e.target.value })}
                    placeholder="main, scraping-v2"
                    className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                    Categoría
                  </label>
                  <input
                    type="text"
                    value={newRepo.category}
                    onChange={(e) => setNewRepo({ ...newRepo, category: e.target.value })}
                    placeholder="Backend, AI/ML, Cloud"
                    className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Prioridad (1 = Destacado en CV, 2 = Secundario)
                </label>
                <select
                  value={newRepo.priority}
                  onChange={(e) => setNewRepo({ ...newRepo, priority: Number(e.target.value) })}
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                >
                  <option value={1}>1 - Principal / Destacado</option>
                  <option value={2}>2 - Secundario</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Notas Técnicas
                </label>
                <input
                  type="text"
                  value={newRepo.notes}
                  onChange={(e) => setNewRepo({ ...newRepo, notes: e.target.value })}
                  placeholder="Microservicio en FastAPI con PostgreSQL..."
                  className="w-full px-3 py-1.5 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 text-xs rounded border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 text-xs rounded bg-teal-600 text-white font-medium hover:bg-teal-700"
                >
                  Agregar a SQLite
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
