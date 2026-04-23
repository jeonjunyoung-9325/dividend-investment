"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { navItems } from "@/components/layout/navigation";
import { cn } from "@/lib/utils";

export function Sidebar({
  mobile = false,
  onNavigate,
}: {
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "flex h-full flex-col justify-between rounded-[2rem] border border-border bg-sidebar p-5",
        mobile ? "min-h-full rounded-none border-0 bg-sidebar px-0 pb-[calc(1.25rem+env(safe-area-inset-bottom))] pt-[calc(1rem+env(safe-area-inset-top))]" : "shadow-soft",
      )}
    >
      <div className="space-y-8">
        <div className="space-y-3 px-5">
          <Badge variant="success" className="w-fit">
            Single-user MVP
          </Badge>
          <div>
            <p className="text-sm text-muted-foreground">Dividend Dashboard</p>
            <h1 className="text-2xl font-semibold tracking-tight text-sidebar-foreground">배당이 쌓이는 흐름</h1>
          </div>
        </div>

        <nav className="space-y-2 px-3">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                className={cn(
                  "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-colors",
                  isActive ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:bg-card/70 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="mx-5 rounded-3xl bg-card p-4">
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Focus</p>
        <p className="mt-2 text-sm leading-6 text-sidebar-foreground">
          수량만 관리하면 현재 비중, 예상 배당, 실제 배당, 미래 성장 흐름까지 한 화면에서 이어집니다.
        </p>
      </div>
    </aside>
  );
}
