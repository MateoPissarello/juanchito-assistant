import React from 'react';
import { Moon, Sun, Terminal, Database, Sparkles, Layers } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface HeaderProps {
  activeTab: 'profile' | 'repos' | 'skills' | 'tailor';
  onTabChange: (tab: 'profile' | 'repos' | 'skills' | 'tailor') => void;
  dbHealthy: boolean;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, onTabChange, dbHealthy }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-950/90 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand & Identity */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-teal-600 dark:bg-teal-500 text-white shadow-sm font-mono font-bold text-base">
            JA
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-zinc-900 dark:text-zinc-100 text-base tracking-tight">
                Juanchito Assistant
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                workbench
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Career Engine & resume.lol Tailoring Studio
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center space-x-1" aria-label="Navegación principal">
          <button
            type="button"
            onClick={() => onTabChange('profile')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'profile'
                ? 'bg-zinc-100 dark:bg-zinc-800 text-teal-700 dark:text-teal-400 font-semibold'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-900'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Perfil & Experiencia</span>
          </button>

          <button
            type="button"
            onClick={() => onTabChange('repos')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'repos'
                ? 'bg-zinc-100 dark:bg-zinc-800 text-teal-700 dark:text-teal-400 font-semibold'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-900'
            }`}
          >
            <Terminal className="w-4 h-4" />
            <span>Repositorios GitHub</span>
          </button>

          <button
            type="button"
            onClick={() => onTabChange('skills')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'skills'
                ? 'bg-zinc-100 dark:bg-zinc-800 text-teal-700 dark:text-teal-400 font-semibold'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-900'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Skills & Certs</span>
          </button>

          <button
            type="button"
            onClick={() => onTabChange('tailor')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'tailor'
                ? 'bg-zinc-100 dark:bg-zinc-800 text-teal-700 dark:text-teal-400 font-semibold'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-900'
            }`}
          >
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Tailoring Studio</span>
          </button>
        </nav>

        {/* Right Actions: DB Indicator & Theme Toggle */}
        <div className="flex items-center space-x-3">
          <div
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-mono border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900"
            title={dbHealthy ? 'Conexión a SQLite activa' : 'Desconectado'}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                dbHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className="text-zinc-600 dark:text-zinc-400">profile.db</span>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            className="p-2 rounded-md text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:outline-none"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
};
