"use client";

import { PropsWithChildren } from "react";
import { MobileBottomNav } from "@/components/layout/mobile-bottom-nav";
import { Sidebar } from "@/components/layout/sidebar";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="grid-surface min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] gap-4 px-3 py-3 sm:gap-6 sm:px-4 sm:py-4 lg:px-6">
        <div className="hidden w-[280px] shrink-0 lg:block">
          <Sidebar />
        </div>

        <div className="flex min-h-[calc(100vh-1.5rem)] flex-1 flex-col overflow-hidden rounded-[1.5rem] border border-border/80 bg-white/75 backdrop-blur-sm sm:min-h-[calc(100vh-2rem)] sm:rounded-[2rem]">
          <div className="sticky top-0 z-20 border-b border-border/80 bg-white/85 px-4 py-3 backdrop-blur-sm lg:hidden">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Dividend Dashboard</p>
              <p className="text-lg font-semibold">배당 대시보드</p>
            </div>
          </div>

          <main className="flex-1 overflow-x-hidden overflow-y-auto p-4 pb-[calc(6.75rem+env(safe-area-inset-bottom))] sm:p-5 sm:pb-[calc(6.75rem+env(safe-area-inset-bottom))] md:p-8 lg:pb-8">
            {children}
          </main>
        </div>
      </div>
      <MobileBottomNav />
    </div>
  );
}
