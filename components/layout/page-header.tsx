import { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0 space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">{eyebrow}</p>
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">{title}</h2>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
      </div>
      {actions ? <div className="flex w-full flex-wrap items-center gap-2 md:w-auto md:justify-end">{actions}</div> : null}
    </div>
  );
}
