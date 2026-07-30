import { X, FileText } from 'lucide-react';
import type { SourceMaterial } from '../../types/course';

interface SourceMaterialsPanelProps {
  materials: SourceMaterial[];
  onClose: () => void;
}

export function SourceMaterialsPanel({ materials, onClose }: SourceMaterialsPanelProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 px-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <p className="font-semibold text-bonsai-text">Source Materials</p>
          <button onClick={onClose} aria-label="Close">
            <X className="h-4 w-4 text-bonsai-text-muted" />
          </button>
        </div>

        <p className="mb-3 text-xs text-bonsai-text-muted">
          The original documents this course was built from, kept separate from web citations.
        </p>

        <ul className="space-y-2">
          {materials.map((material) => {
            const content = (
              <div className="flex items-center gap-3 rounded-lg border border-bonsai-border px-3 py-2.5 text-sm">
                <FileText className="h-4 w-4 shrink-0 text-bonsai-text-muted" />
                <span className="truncate text-bonsai-text">{material.fileName}</span>
              </div>
            );

            return (
              <li key={material.id}>
                {material.url ? (
                  <a href={material.url} target="_blank" rel="noreferrer" className="block hover:bg-bonsai-cream">
                    {content}
                  </a>
                ) : (
                  content
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
