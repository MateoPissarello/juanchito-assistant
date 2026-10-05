import React, { useState } from 'react';
import { Plus, X, Trash2 } from 'lucide-react';
import type { SkillCategory } from '../../types/profile';
import { api } from '../../services/api';

interface SkillsCanvasProps {
  skills: SkillCategory[];
  onReload: () => void;
}

export const SkillsCanvas: React.FC<SkillsCanvasProps> = ({ skills, onReload }) => {
  const [newSkillInput, setNewSkillInput] = useState<Record<number, string>>({});
  const [showAddCat, setShowAddCat] = useState(false);
  const [newCatName, setNewCatName] = useState('');

  const handleAddSkill = async (cat: SkillCategory) => {
    if (!cat.id) return;
    const name = (newSkillInput[cat.id] || '').trim();
    if (!name) return;

    if (cat.skills.includes(name)) {
      alert('La habilidad ya existe en la categoría');
      return;
    }

    try {
      await api.updateSkillCategory(cat.id, [...cat.skills, name]);
      setNewSkillInput((prev) => ({ ...prev, [cat.id!]: '' }));
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al agregar habilidad');
    }
  };

  const handleRemoveSkill = async (cat: SkillCategory, skillToRemove: string) => {
    if (!cat.id) return;
    try {
      await api.updateSkillCategory(
        cat.id,
        cat.skills.filter((s) => s !== skillToRemove)
      );
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al remover habilidad');
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatName.trim()) return;
    try {
      await api.createSkillCategory(newCatName.trim(), []);
      setNewCatName('');
      setShowAddCat(false);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al crear categoría');
    }
  };

  const handleDeleteCategory = async (cat: SkillCategory) => {
    if (!cat.id) return;
    if (!confirm(`¿Eliminar la categoría "${cat.category}"?`)) return;
    try {
      await api.deleteSkillCategory(cat.id);
      onReload();
    } catch (err: any) {
      alert(err.message || 'Error al eliminar categoría');
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 sm:px-6">
      <div className="flex items-center justify-between pb-4 mb-6 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 font-mono tracking-tight">
            Technical Skill Inventory
          </h1>
          <p className="text-xs text-zinc-500 font-mono mt-0.5">
            Clasificación de tecnologías para optimizar el ATS Keyword Matcher
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowAddCat(!showAddCat)}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Category</span>
        </button>
      </div>

      {showAddCat && (
        <form onSubmit={handleCreateCategory} className="border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-900 p-4 mb-6 flex items-center space-x-2 text-xs font-mono">
          <input
            type="text"
            required
            placeholder="Category name (ej. Embedded Systems)"
            value={newCatName}
            onChange={(e) => setNewCatName(e.target.value)}
            className="flex-1 px-2.5 py-1.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
          />
          <button
            type="submit"
            className="px-3 py-1.5 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-semibold"
          >
            Create
          </button>
          <button
            type="button"
            onClick={() => setShowAddCat(false)}
            className="px-2.5 py-1.5 rounded border border-zinc-200 dark:border-zinc-800 text-zinc-500"
          >
            Cancel
          </button>
        </form>
      )}

      <div className="space-y-4">
        {skills.map((cat) => (
          <div
            key={cat.id}
            className="border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900/60 p-4 font-mono text-xs"
          >
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-zinc-100 dark:border-zinc-800/80">
              <span className="font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider text-[11px]">
                {cat.category}
              </span>

              <button
                type="button"
                onClick={() => handleDeleteCategory(cat)}
                className="text-zinc-400 hover:text-rose-600 p-0.5"
                title="Eliminar categoría"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Chips */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              {cat.skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 text-xs border border-zinc-200 dark:border-zinc-700"
                >
                  <span>{skill}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(cat, skill)}
                    className="text-zinc-400 hover:text-rose-500 p-0.5"
                  >
                    <X className="w-2.5 h-2.5" />
                  </button>
                </span>
              ))}
            </div>

            {/* In-place quick add */}
            {cat.id && (
              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="text"
                  placeholder={`+ add to ${cat.category}...`}
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
                  className="px-2 py-1 text-xs rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-zinc-400"
                />
                <button
                  type="button"
                  onClick={() => handleAddSkill(cat)}
                  className="px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700"
                >
                  add
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
