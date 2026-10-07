import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] px-3 py-1 text-sm text-slate-900 dark:text-[#F5F7FA] shadow-xs transition-all placeholder:text-slate-400 dark:placeholder:text-[#94A8B8] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[#FF7A18] focus-visible:border-[#FF7A18] disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-slate-100 dark:disabled:bg-[#061526]",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
