import * as React from "react"
import { cn } from "@/lib/utils"
import { AlertCircle, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  message: string
  onRetry?: () => void
  retryText?: string
  variant?: "banner" | "card"
}

export function ErrorState({
  title,
  message,
  onRetry,
  retryText = "Retry",
  variant = "banner",
  className,
  ...props
}: ErrorStateProps) {
  if (variant === "card") {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center",
          className
        )}
        {...props}
      >
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">{title || "An error occurred"}</h3>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground leading-relaxed">
          {message}
        </p>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="mt-4 gap-1.5 border-destructive/30 hover:bg-destructive/10"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            {retryText}
          </Button>
        )}
      </div>
    )
  }

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-3.5 text-xs text-destructive",
        className
      )}
      {...props}
    >
      <div className="flex items-start gap-2.5">
        <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          {title && <span className="font-semibold block">{title}</span>}
          <span className="text-foreground/90">{message}</span>
        </div>
      </div>
      {onRetry && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onRetry}
          className="h-7 text-xs text-destructive hover:bg-destructive/20 shrink-0"
        >
          <RotateCcw className="h-3 w-3 mr-1" />
          {retryText}
        </Button>
      )}
    </div>
  )
}
