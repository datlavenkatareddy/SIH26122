import * as React from "react"

import { cn } from "@/lib/utils"

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "flex min-h-[80px] w-full rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] px-3 py-2 text-sm text-slate-900 dark:text-[#F5F7FA] shadow-xs transition-all placeholder:text-slate-400 dark:placeholder:text-[#94A8B8] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#FF7A18] focus-visible:border-[#FF7A18] disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-slate-100 dark:disabled:bg-[#061526]",
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = "Textarea"

export { Textarea }
