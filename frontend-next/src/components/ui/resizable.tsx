"use client"

import * as React from "react"
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"
import * as ResizablePrimitive from "react-resizable-panels"

import { cn } from "@/lib/utils"

function ResizablePanelGroup({
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.Group>) {
  return (
    <ResizablePrimitive.Group
      data-slot="resizable-panel-group"
      className={cn(
        "flex h-full w-full aria-[orientation=vertical]:flex-col",
        className
      )}
      {...props}
    />
  )
}

function ResizablePanel({
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.Panel>) {
  return <ResizablePrimitive.Panel data-slot="resizable-panel" {...props} />
}

function ResizableHandle({
  withHandle,
  onCollapseClick,
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.Separator> & {
  withHandle?: boolean
  /** LeetCode-style yopish tugmasi bosilganda chaqiriladi (masalan, chap panelni yopish uchun) */
  onCollapseClick?: () => void
}) {
  return (
    <ResizablePrimitive.Separator
      data-slot="resizable-handle"
      className={cn(
        "group relative flex items-center justify-center bg-transparent",
        "aria-[orientation=vertical]:h-full aria-[orientation=vertical]:w-2.5",
        "aria-[orientation=horizontal]:h-2.5 aria-[orientation=horizontal]:w-full",
        "focus-visible:outline-none",
        className
      )}
      {...props}
    >
      {/* Markaziy chiziq: default holatda ingichka, hover/drag paytida to'liq ko'k */}
      <div
        className={cn(
          "pointer-events-none absolute rounded-full bg-neutral-200 transition-colors dark:bg-neutral-700",
          "group-aria-[orientation=vertical]:inset-y-0 group-aria-[orientation=vertical]:left-1/2 group-aria-[orientation=vertical]:w-[2px] group-aria-[orientation=vertical]:-translate-x-1/2",
          "group-aria-[orientation=horizontal]:inset-x-0 group-aria-[orientation=horizontal]:top-1/2 group-aria-[orientation=horizontal]:h-[2px] group-aria-[orientation=horizontal]:-translate-y-1/2",
          "group-hover:bg-blue-400 group-active:bg-blue-500 group-focus-visible:bg-blue-500"
        )}
      />

      {/* Grip - hover paytida chiqadi (LeetCode'dagidek) */}
      {withHandle && (
        <div
          className={cn(
            "z-10 flex items-center justify-center rounded-sm border border-neutral-200 bg-white opacity-0 shadow-sm transition-opacity dark:border-neutral-700 dark:bg-neutral-900",
            "group-hover:opacity-100 group-active:opacity-100",
            "group-aria-[orientation=vertical]:h-8 group-aria-[orientation=vertical]:w-3",
            "group-aria-[orientation=horizontal]:h-3 group-aria-[orientation=horizontal]:w-8"
          )}
        >
          <div className="h-4 w-[3px] rounded-full bg-neutral-300 group-aria-[orientation=horizontal]:h-[3px] group-aria-[orientation=horizontal]:w-4 dark:bg-neutral-600" />
        </div>
      )}

      {/* Tepadagi "yopish" tugmasi - faqat vertikal (chap/o'ng) handle uchun, hover paytida chiqadi */}
      {onCollapseClick && (
        <button
          type="button"
          onClick={onCollapseClick}
          className={cn(
            "absolute top-2 z-20 flex h-6 w-6 items-center justify-center rounded-full border border-neutral-200 bg-white text-neutral-500 opacity-0 shadow-sm transition-opacity hover:bg-neutral-100 hover:text-neutral-800 group-hover:opacity-100 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800",
            "left-1/2 -translate-x-1/2"
          )}
          aria-label="Panelni yopish/ochish"
        >
          <ChevronLeftIcon className="size-3.5" />
        </button>
      )}
    </ResizablePrimitive.Separator>
  )
}

export { ResizablePanelGroup, ResizablePanel, ResizableHandle }