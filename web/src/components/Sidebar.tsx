import React from 'react';
import {
  User,
  Briefcase,
  Terminal,
  Award,
  Sparkles,
  Plus,
  ChevronRight,
  FolderGit2,
} from 'lucide-react';
import type { WorkExperience } from '../types/profile';

export type NavigationTarget =
  | { view: 'personal' }
  | { view: 'experience'; expId?: number }
  | { view: 'repos' }
  | { view: 'skills' }
  | { view: 'certs' }
  | { view: 'tailor' };

interface SidebarProps {
  currentNav: NavigationTarget;
  onNavigate: (target: NavigationTarget) => void;
  experiences: WorkExperience[];
  repoCount: number;
  activeRepoCount: number;
  skillCategoryCount: number;
  certCount: number;
  onNewCompany: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentNav,
  onNavigate,
  experiences,
  repoCount,
  activeRepoCount,
  skillCategoryCount,
  certCount,
  onNewCompany,
}) => {
  const isPersonalActive = currentNav.view === 'personal';
  const isReposActive = currentNav.view === 'repos';
  const isSkillsActive = currentNav.view === 'skills';
  const isCertsActive = currentNav.view === 'certs';
  const isTailorActive = currentNav.view === 'tailor';

  return (
    <aside className="w-64 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/70 flex flex-col shrink-0 select-none overflow-y-auto">
      {/* Section 1: Perfil y Datos Base */}
      <div className="p-3 border-b border-zinc-200/60 dark:border-zinc-800/60">
        <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold px-2 mb-1 block">
          Document Structure
        </span>

        <button
          type="button"
          onClick={() => onNavigate({ view: 'personal' })}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors font-medium ${
            isPersonalActive
              ? 'bg-zinc-200/80 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold'
              : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:text-zinc-900 dark:hover:text-zinc-200'
          }`}
        >
          <div className="flex items-center space-x-2">
            <User className="w-3.5 h-3.5 text-zinc-500" />
            <span>Header & Variables</span>
          </div>
          <span className="font-mono text-[10px] text-zinc-400">@NAME</span>
        </button>
      </div>

      {/* Section 2: Experiencia e Iniciativas */}
      <div className="p-3 border-b border-zinc-200/60 dark:border-zinc-800/60">
        <div className="flex items-center justify-between px-2 mb-1.5">
          <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold">
            Work Experience
          </span>
          <button
            type="button"
            onClick={onNewCompany}
            className="text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 p-0.5 rounded"
            title="Agregar nueva empresa"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="space-y-0.5">
          {experiences.map((exp) => {
            const isSelected = currentNav.view === 'experience' && currentNav.expId === exp.id;
            return (
              <button
                key={exp.id}
                type="button"
                onClick={() => onNavigate({ view: 'experience', expId: exp.id })}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors text-left ${
                  isSelected
                    ? 'bg-zinc-200/80 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold'
                    : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:text-zinc-900 dark:hover:text-zinc-200'
                }`}
              >
                <div className="flex items-center space-x-2 truncate">
                  <Briefcase className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span className="truncate">{exp.company}</span>
                </div>
                <span className="font-mono text-[10px] text-zinc-400 shrink-0 ml-1">
                  {exp.projects?.length || 0}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Section 3: Repositorios Seguidos */}
      <div className="p-3 border-b border-zinc-200/60 dark:border-zinc-800/60">
        <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold px-2 mb-1 block">
          Ingestion & Repos
        </span>

        <button
          type="button"
          onClick={() => onNavigate({ view: 'repos' })}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors ${
            isReposActive
              ? 'bg-zinc-200/80 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold'
              : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:text-zinc-900 dark:hover:text-zinc-200'
          }`}
        >
          <div className="flex items-center space-x-2">
            <FolderGit2 className="w-3.5 h-3.5 text-zinc-500" />
            <span>Tracked Repos</span>
          </div>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-zinc-200/60 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
            {activeRepoCount}/{repoCount}
          </span>
        </button>
      </div>

      {/* Section 4: Skills y Certificaciones */}
      <div className="p-3 border-b border-zinc-200/60 dark:border-zinc-800/60 space-y-1">
        <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold px-2 mb-1 block">
          Technical Inventory
        </span>

        <button
          type="button"
          onClick={() => onNavigate({ view: 'skills' })}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors ${
            isSkillsActive
              ? 'bg-zinc-200/80 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold'
              : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:text-zinc-900 dark:hover:text-zinc-200'
          }`}
        >
          <div className="flex items-center space-x-2">
            <Terminal className="w-3.5 h-3.5 text-zinc-500" />
            <span>Skill Matrix</span>
          </div>
          <span className="font-mono text-[10px] text-zinc-400">{skillCategoryCount} cat</span>
        </button>

        <button
          type="button"
          onClick={() => onNavigate({ view: 'certs' })}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors ${
            isCertsActive
              ? 'bg-zinc-200/80 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold'
              : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:text-zinc-900 dark:hover:text-zinc-200'
          }`}
        >
          <div className="flex items-center space-x-2">
            <Award className="w-3.5 h-3.5 text-zinc-500" />
            <span>Certifications</span>
          </div>
          <span className="font-mono text-[10px] text-zinc-400">{certCount}</span>
        </button>
      </div>

      {/* Section 5: Tailoring Studio */}
      <div className="p-3 mt-auto border-t border-zinc-200/60 dark:border-zinc-800/60">
        <button
          type="button"
          onClick={() => onNavigate({ view: 'tailor' })}
          className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition-colors border ${
            isTailorActive
              ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 border-transparent font-medium'
              : 'border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:border-zinc-400 dark:hover:border-zinc-600'
          }`}
        >
          <div className="flex items-center space-x-2">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            <span className="font-semibold">Tailoring Studio</span>
          </div>
          <ChevronRight className="w-3 h-3 text-zinc-400" />
        </button>
      </div>
    </aside>
  );
};
