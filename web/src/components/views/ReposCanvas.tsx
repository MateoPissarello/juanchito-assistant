import React, { useState } from 'react';
import {
  ExternalLink,
  Plus,
  Trash2,
  GitBranch,
  X,
  Search,
} from 'lucide-react';
import type { TrackedRepo } from '../../types/profile';
import { api } from '../../services/api';

interface ReposCanvasProps {
  repos: TrackedRepo[];
  githubUser: string;
  onReload: () => void;
}

export const ReposCanvas: React.FC<ReposCanvasProps> = ({ repos, githubUser, onReload }) => {
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [search, setSearch] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
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
      alert(err.message || 'Error al alternar');
    }
  };

  const handleDelete = async (repo: TrackedRepo) => {
    if (!repo.id) return;
    if (!confirm(`¿Remover '${repo.name}' de los repositorios seguidos?`)) return;
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
      setShowAddForm(false);
      setNewRepo({ name: '', branch: '', category: 'Backend', priority: 1, notes: '' });
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al agregar');
    }
  };

  const filtered = repos.filter((r) => {
    if (filter === 'active' && !r.is_active) return false;
    if (filter === 'inactive' && r.is_active) return false;
    if (search && !r.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const activeCount = repos.filter((r) => r.is_active).length;

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 sm:px-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-4 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 font-mono tracking-tight">
            Tracked Repositories (GitHubIngestService)
          </h1>
          <p className="text-xs text-zinc-500 font-mono mt-0.5">
            Configuración persistente en SQLite ({activeCount} activos de {repos.length} repos)
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowAddForm(!showAddForm)}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Track New Repo</span>
        </button>
      </div>

      {/* Add Repo Inline Form */}
      {showAddForm && (
        <form onSubmit={handleCreate} className="border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 p-4 mb-6 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-100 dark:border-zinc-800">
            <span className="text-xs font-mono font-semibold text-zinc-900 dark:text-zinc-100">
              Track Repository in SQLite
            </span>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div>
              <label className="text-zinc-400 block mb-1">Repo Name</label>
              <input
                type="text"
                required
                placeholder="ej: goofish-scraping"
                value={newRepo.name}
                onChange={(e) => setNewRepo({ ...newRepo, name: e.target.value })}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 font-mono"
              />
            </div>
            <div>
              <label className="text-zinc-400 block mb-1">Branch Override</label>
              <input
                type="text"
                placeholder="main, scraping-v2"
                value={newRepo.branch}
                onChange={(e) => setNewRepo({ ...newRepo, branch: e.target.value })}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 font-mono"
              />
            </div>
            <div>
              <label className="text-zinc-400 block mb-1">Category</label>
              <input
                type="text"
                placeholder="Backend, AI/ML"
                value={newRepo.category}
                onChange={(e) => setNewRepo({ ...newRepo, category: e.target.value })}
                className="w-full px-2 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 font-mono"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-2 text-xs font-mono">
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
              save repo
            </button>
          </div>
        </form>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 text-xs font-mono">
        <div className="flex items-center space-x-1 border border-zinc-200 dark:border-zinc-800 rounded p-0.5 bg-zinc-50 dark:bg-zinc-950">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`px-2.5 py-1 rounded transition-colors ${
              filter === 'all'
                ? 'bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            All ({repos.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('active')}
            className={`px-2.5 py-1 rounded transition-colors ${
              filter === 'active'
                ? 'bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            Active ({activeCount})
          </button>
          <button
            type="button"
            onClick={() => setFilter('inactive')}
            className={`px-2.5 py-1 rounded transition-colors ${
              filter === 'inactive'
                ? 'bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            Inactive ({repos.length - activeCount})
          </button>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-2" />
          <input
            type="text"
            placeholder="Search repos..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 text-xs font-mono focus:outline-none focus:border-zinc-400"
          />
        </div>
      </div>

      {/* Engineering Data Table */}
      <div className="border border-zinc-200 dark:border-zinc-800 rounded overflow-hidden bg-white dark:bg-zinc-900/60">
        <table className="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 text-zinc-500 uppercase tracking-wider text-[10px]">
              <th className="py-2.5 px-3">State</th>
              <th className="py-2.5 px-3">Repository</th>
              <th className="py-2.5 px-3">Branch</th>
              <th className="py-2.5 px-3">Category</th>
              <th className="py-2.5 px-3 text-center">Priority</th>
              <th className="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/80">
            {filtered.map((repo) => (
              <tr
                key={repo.id}
                className={`hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors ${
                  !repo.is_active ? 'opacity-50' : ''
                }`}
              >
                {/* State switch */}
                <td className="py-2 px-3">
                  <button
                    type="button"
                    onClick={() => handleToggle(repo)}
                    className={`inline-block w-2.5 h-2.5 rounded-full transition-colors ${
                      repo.is_active ? 'bg-emerald-500' : 'bg-zinc-300 dark:bg-zinc-600'
                    }`}
                    title={repo.is_active ? 'Activo (haz clic para desactivar)' : 'Inactivo'}
                  />
                </td>

                {/* Repository Name & Link */}
                <td className="py-2 px-3 font-semibold text-zinc-900 dark:text-zinc-100">
                  <a
                    href={`https://github.com/${githubUser}/${repo.name}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-1 hover:underline"
                  >
                    <span>{repo.name}</span>
                    <ExternalLink className="w-3 h-3 text-zinc-400" />
                  </a>
                </td>

                {/* Branch */}
                <td className="py-2 px-3 text-zinc-600 dark:text-zinc-400">
                  {repo.branch ? (
                    <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[11px]">
                      <GitBranch className="w-2.5 h-2.5 text-zinc-400" />
                      <span>{repo.branch}</span>
                    </span>
                  ) : (
                    <span className="text-zinc-400 italic">default</span>
                  )}
                </td>

                {/* Category */}
                <td className="py-2 px-3 text-zinc-600 dark:text-zinc-400">
                  {repo.category || <span className="text-zinc-400 italic">—</span>}
                </td>

                {/* Priority */}
                <td className="py-2 px-3 text-center text-zinc-500">
                  P{repo.priority}
                </td>

                {/* Delete */}
                <td className="py-2 px-3 text-right">
                  <button
                    type="button"
                    onClick={() => handleDelete(repo)}
                    className="text-zinc-400 hover:text-rose-600 p-1"
                    title="Remover de SQLite"
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
