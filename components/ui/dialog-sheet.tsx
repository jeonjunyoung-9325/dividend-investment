"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { PropsWithChildren } from "react";
import { cn } from "@/lib/utils";

export function Sheet({
  open,
  onOpenChange,
  children,
}: PropsWithChildren<{ open: boolean; onOpenChange: (open: boolean) => void }>) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {children}
    </Dialog.Root>
  );
}

export const SheetTrigger = Dialog.Trigger;

export function SheetContent({
  children,
  className,
  side = "right",
}: PropsWithChildren<{ className?: string; side?: "right" | "bottom" }>) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" />
      <Dialog.Content
        className={cn(
          "fixed z-50 flex overflow-y-auto border-border bg-card p-5 shadow-soft",
          side === "right" && "inset-y-0 right-0 w-[88vw] max-w-sm flex-col border-l",
          side === "bottom" && "inset-x-0 bottom-0 max-h-[85vh] flex-col border-t",
          className,
        )}
      >
        <Dialog.Close className="absolute right-4 top-4 rounded-full p-2 text-muted-foreground hover:bg-muted">
          <X className="h-4 w-4" />
        </Dialog.Close>
        {children}
      </Dialog.Content>
    </Dialog.Portal>
  );
}
