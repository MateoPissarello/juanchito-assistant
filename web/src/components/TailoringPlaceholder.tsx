import React from 'react';
import { Sparkles, Terminal, CheckCircle2 } from 'lucide-react';

export const TailoringPlaceholder: React.FC = () => {
  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-8 text-center max-w-2xl mx-auto my-12 transition-colors">
      <div className="w-12 h-12 rounded-full bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800 text-teal-600 dark:text-teal-400 flex items-center justify-center mx-auto mb-4">
        <Sparkles className="w-6 h-6" />
      </div>

      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
        Tailoring Studio & Split-View (Próxima Fase)
      </h2>

      <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed mb-6">
        El motor multi-agente ya está 100% operativo en la terminal mediante{' '}
        <code className="px-1.5 py-0.5 rounded font-mono bg-zinc-100 dark:bg-zinc-800 text-teal-600 dark:text-teal-400">
          juanchito tailor
        </code>
        . En la siguiente iteración incorporaremos la vista web side-by-side con renderizado en vivo para resume.lol.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left mb-6">
        <div className="p-3 rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            <span>JobAnalyzer</span>
          </div>
          <p className="text-[11px] text-zinc-500">
            Descarga URLs y extrae requisitos ATS con LLM estructurado.
          </p>
        </div>

        <div className="p-3 rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            <span>Matcher & Writer</span>
          </div>
          <p className="text-[11px] text-zinc-500">
            Selecciona iniciativas y redacta viñetas Google XYZ para 1 página.
          </p>
        </div>

        <div className="p-3 rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            <span>Jev Router</span>
          </div>
          <p className="text-[11px] text-zinc-500">
            Auditoría determinista de 100 pts ATS con bucle de auto-mejora.
          </p>
        </div>
      </div>

      <div className="p-3 rounded-md bg-zinc-100 dark:bg-zinc-800/60 text-xs font-mono text-zinc-700 dark:text-zinc-300 inline-flex items-center space-x-2">
        <Terminal className="w-4 h-4 text-teal-600 dark:text-teal-400" />
        <span>Prueba mientras tanto en consola: uv run juanchito tailor</span>
      </div>
    </div>
  );
};
