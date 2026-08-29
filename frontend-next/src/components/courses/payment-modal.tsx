// src/components/courses/payment-modal.tsx
"use client";

import { X } from "lucide-react";

interface PaymentModalProps {
  open: boolean;
  onClose: () => void;
  amount: string;
  courseTitle: string;
}

export function PaymentModal({ open, onClose, amount, courseTitle }: PaymentModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        className="relative w-full max-w-sm overflow-hidden rounded-xl border bg-white shadow-xl"
        style={{ borderColor: "var(--line)" }}
      >
        <div
          className="font-ledger flex items-center justify-between border-b px-5 py-2.5 text-[11px]"
          style={{ borderColor: "var(--line)", color: "var(--ink)", opacity: 0.5 }}
        >
          <span>payment.sh</span>
          <button
            onClick={onClose}
            className="transition-colors hover:text-[var(--ink)]"
            style={{ opacity: 0.8 }}
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="p-6 text-center">
          <h3 className="font-display text-lg font-bold" style={{ color: "var(--ink)" }}>
            To'lovni amalga oshiring
          </h3>
          <p className="mt-1 text-sm" style={{ color: "var(--ink)", opacity: 0.5 }}>
            "{courseTitle}"
          </p>
        </div>

        <div
          className="border-t px-6 py-4 text-center"
          style={{ borderColor: "var(--line)" }}
        >
          <div className="font-display text-3xl font-bold" style={{ color: "var(--ink)" }}>
            {Number(amount).toLocaleString()}{" "}
            <span className="text-base font-normal" style={{ opacity: 0.5 }}>
              so'm
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t p-6" style={{ borderColor: "var(--line)" }}>
          <button
            className="font-ledger w-full rounded-lg py-3 text-sm font-medium text-white transition hover:opacity-90"
            style={{ backgroundColor: "var(--blue)" }}
          >
            $ click orqali to'lash
          </button>
          <button
            className="font-ledger w-full rounded-lg border py-3 text-sm font-medium transition hover:bg-[var(--bone)]"
            style={{ borderColor: "var(--line)", color: "var(--ink)" }}
          >
            $ payme orqali to'lash
          </button>
        </div>
      </div>
    </div>
  );
}