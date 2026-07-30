import type { ReactNode } from 'react';
import { Card } from '../ui/Card';

export function InfoPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">{title}</h1>
      <Card className="mt-6 space-y-4 text-sm leading-relaxed text-bonsai-text">{children}</Card>
    </div>
  );
}
