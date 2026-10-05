import React, { useMemo } from 'react';
import { marked } from 'marked';

interface LiveResumePreviewProps {
  markdown: string;
}

export const LiveResumePreview: React.FC<LiveResumePreviewProps> = ({ markdown }) => {
  const htmlContent = useMemo(() => {
    if (!markdown.trim()) return '';

    // 1. Extraer variables @VAR=valor||fake
    const vars: Record<string, string> = {};
    const lines = markdown.split('\n');
    const contentLines: string[] = [];
    let inComment = false;

    for (const line of lines) {
      const trimmed = line.trim();

      if (trimmed.startsWith('<!--')) {
        inComment = true;
        continue;
      }
      if (inComment) {
        if (trimmed.includes('-->')) inComment = false;
        continue;
      }

      if (trimmed.startsWith('@') && trimmed.includes('=')) {
        const eqIdx = trimmed.indexOf('=');
        const varName = trimmed.slice(1, eqIdx).trim();
        const rawVal = trimmed.slice(eqIdx + 1).trim();
        // Quitar la parte de fallback fake si existe
        const actualVal = rawVal.split('||')[0].trim();
        vars[varName] = actualVal;
        continue;
      }

      contentLines.push(line);
    }

    let processedMarkdown = contentLines.join('\n');

    // 2. Reemplazar {VAR} por sus valores
    for (const [k, v] of Object.entries(vars)) {
      const regex = new RegExp(`\\{${k}\\}`, 'g');
      processedMarkdown = processedMarkdown.replace(regex, v);
    }

    // 3. Parsear a HTML con marked manteniendo las etiquetas HTML intactas
    marked.setOptions({
      breaks: false,
      gfm: true,
    });

    try {
      return marked.parse(processedMarkdown) as string;
    } catch (err) {
      console.error('Error rendering markdown to html:', err);
      return `<p class="text-rose-500 font-mono text-xs">Error al procesar el formato Markdown</p>`;
    }
  }, [markdown]);

  if (!markdown.trim()) {
    return (
      <div className="h-full flex items-center justify-center p-8 text-center text-zinc-400 font-mono text-xs">
        <p>El currículum optimizado aparecerá aquí con el diseño exacto de resume.lol.</p>
      </div>
    );
  }

  return (
    <div className="resume-print-wrapper p-4 sm:p-6 flex justify-center">
      {/* Contenedor tipo Hoja A4/Letter de resume.lol */}
      <div
        id="resume-print-paper"
        className="resume-paper w-full max-w-[800px] min-h-[1050px] p-8 sm:p-12 bg-white text-black shadow-2xl rounded-sm border border-zinc-300 dark:border-zinc-700"
        dangerouslySetInnerHTML={{ __html: htmlContent }}
      />
    </div>
  );
};
