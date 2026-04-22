"use client";

import { Menu } from "lucide-react";
import { PropsWithChildren, useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/dialog-sheet";

export function AppShell({ children }: PropsWithChildren) {
  const [open, setOpen] = useState(false);

  return (
    <div className="grid-surface min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] gap-6 px-4 py-4 lg:px-6">
        <div className="hidden w-[280px] shrink-0 lg:block">
          <Sidebar />
        </div>

        <div className="flex min-h-[calc(100vh-2rem)] flex-1 flex-col overflow-hidden rounded-[2rem] border border-border/80 bg-white/75 backdrop-blur-sm">
          <div className="flex items-center justify-between border-b border-border/80 px-5 py-4 lg:hidden">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Dividend Dashboard</p>
              <p className="text-lg font-semibold">배당 대시보드</p>
            </div>
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent>
                <Sidebar mobile />
              </SheetContent>
            </Sheet>
          </div>

          <main className="flex-1 overflow-y-auto p-5 md:p-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
