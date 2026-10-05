import React, { useState } from 'react';
import type { EvaluationResult } from '../../types/profile';
import { CheckCircle2, AlertTriangle, ChevronDown, ChevronUp, ShieldCheck } from 'lucide-react';

interface ScorecardViewProps {
  evaluation: EvaluationResult;
}

export const ScorecardView: React.FC<ScorecardViewProps> = ({ evaluation }) => {
  const [expanded, setExpanded] = useState(false);
  const isApproved = evaluation.total_score >= 85 || evaluation.decision === 'APPROVE';

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4 transition-colors shadow-xs">
      {/* Header Compacto con Score */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center font-mono font-bold text-sm shrink-0 ${
              isApproved
                ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                : 'bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
            }`}
          >
            {evaluation.total_score}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-zinc-500" />
                <span>Auditoría de Compatibilidad ATS</span>
              </h3>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-medium ${
                  isApproved
                    ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
                    : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
                }`}
              >
                {isApproved ? 'Listo para postulación' : 'En optimización'}
              </span>
            </div>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
              Evaluación sobre 100 puntos basada en palabras clave, relevancia y formato.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center justify-center space-x-1 px-2.5 py-1 text-xs font-medium rounded border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 self-start sm:self-auto cursor-pointer"
        >
          <span>{expanded ? 'Ocultar desglose' : 'Ver desglose'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Desglose Expandible */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800 space-y-4 text-xs">
          {/* Métricas por Categoría */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono">
            <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800/80">
              <span className="text-[10px] text-zinc-500 uppercase block mb-1">Keywords ATS</span>
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {evaluation.breakdown.ats_keyword_match}
                <span className="text-[10px] text-zinc-400 font-normal"> / 25</span>
              </span>
            </div>

            <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800/80">
              <span className="text-[10px] text-zinc-500 uppercase block mb-1">Relevancia</span>
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {evaluation.breakdown.role_relevance}
                <span className="text-[10px] text-zinc-400 font-normal"> / 25</span>
              </span>
            </div>

            <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800/80">
              <span className="text-[10px] text-zinc-500 uppercase block mb-1">Métricas XYZ</span>
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {evaluation.breakdown.quantifiable_impact}
                <span className="text-[10px] text-zinc-400 font-normal"> / 20</span>
              </span>
            </div>

            <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800/80">
              <span className="text-[10px] text-zinc-500 uppercase block mb-1">Veracidad</span>
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {evaluation.breakdown.factual_integrity}
                <span className="text-[10px] text-zinc-400 font-normal"> / 15</span>
              </span>
            </div>

            <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800/80 col-span-2 sm:col-span-1">
              <span className="text-[10px] text-zinc-500 uppercase block mb-1">Formato 1 Pág</span>
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {evaluation.breakdown.format_and_length}
                <span className="text-[10px] text-zinc-400 font-normal"> / 15</span>
              </span>
            </div>
          </div>

          {/* Fortalezas y Recomendaciones */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {evaluation.strengths.length > 0 && (
              <div className="p-3 rounded bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800">
                <h4 className="text-[11px] font-semibold text-zinc-900 dark:text-zinc-200 flex items-center space-x-1.5 mb-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Puntos Fuertes Identificados</span>
                </h4>
                <ul className="space-y-1.5">
                  {evaluation.strengths.map((str, idx) => (
                    <li key={idx} className="text-[11px] text-zinc-600 dark:text-zinc-400 flex items-start space-x-2">
                      <span className="text-emerald-500 font-bold">•</span>
                      <span>{str}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {evaluation.actionable_improvements.length > 0 && (
              <div className="p-3 rounded bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800">
                <h4 className="text-[11px] font-semibold text-zinc-900 dark:text-zinc-200 flex items-center space-x-1.5 mb-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  <span>Recomendaciones para Entrevistas</span>
                </h4>
                <ul className="space-y-1.5">
                  {evaluation.actionable_improvements.map((imp, idx) => (
                    <li key={idx} className="text-[11px] text-zinc-600 dark:text-zinc-400 flex items-start space-x-2">
                      <span className="text-amber-500 font-bold">•</span>
                      <span>{imp}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
