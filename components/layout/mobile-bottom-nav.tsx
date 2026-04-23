"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { mobileMoreIcon, mobileOverflowNavItems, mobilePrimaryNavItems } from "@/components/layout/navigation";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/dialog-sheet";
import { cn } from "@/lib/utils";

export function MobileBottomNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const MoreIcon = mobileMoreIcon;
  const moreActive = mobileOverflowNavItems.some((item) => pathname === item.href);

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border/80 bg-white/95 px-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-2 backdrop-blur-sm lg:hidden">
      <div className="mx-auto flex max-w-[640px] items-center justify-between gap-1 rounded-[1.75rem] border border-border/70 bg-white/90 p-1.5 shadow-[0_-8px_24px_rgba(15,23,42,0.08)]">
        {mobilePrimaryNavItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-w-0 flex-1 flex-col items-center gap-1 rounded-2xl px-2 py-2 text-[11px] font-medium transition-colors",
                isActive ? "bg-sidebar text-foreground" : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}

        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                "flex h-auto min-w-0 flex-1 flex-col gap-1 rounded-2xl px-2 py-2 text-[11px] font-medium",
                moreActive ? "bg-sidebar text-foreground" : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
              )}
            >
              <MoreIcon className="h-4 w-4 shrink-0" />
              <span className="truncate">더보기</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="bottom" className="max-h-[85vh] rounded-t-[2rem] p-0">
            <div className="space-y-6 bg-sidebar px-4 pb-[calc(1.25rem+env(safe-area-inset-bottom))] pt-5">
              <div className="px-2">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">More</p>
                <p className="mt-2 text-lg font-semibold text-sidebar-foreground">추가 메뉴</p>
              </div>

              <nav className="space-y-2">
                {mobileOverflowNavItems.map((item) => {
                  const isActive = pathname === item.href;
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setOpen(false)}
                      className={cn(
                        "flex items-center gap-3 rounded-2xl px-4 py-4 text-sm font-medium transition-colors",
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
          </SheetContent>
        </Sheet>
      </div>
    </div>
  );
}
