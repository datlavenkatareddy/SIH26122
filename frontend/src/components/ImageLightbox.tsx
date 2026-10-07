import React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

/**
 * Accessible click-to-enlarge image viewer (ISS-20). Built on the same Radix
 * Dialog primitive as components/ui/dialog.tsx (not a new dependency) so
 * Escape-to-close, focus trapping, and overlay-click-to-close come for free.
 */
export interface ImageLightboxProps {
  src: string;
  alt: string;
  /** Small trigger element (a thumbnail) that opens the lightbox on click. */
  children: React.ReactNode;
  triggerClassName?: string;
}

export function ImageLightbox({ src, alt, children, triggerClassName }: ImageLightboxProps) {
  const { t } = useTranslation();
  return (
    <DialogPrimitive.Root>
      <DialogPrimitive.Trigger asChild>
        <button
          type="button"
          className={cn('cursor-zoom-in rounded-lg overflow-hidden focus:outline-hidden focus-visible:ring-2 focus-visible:ring-primary', triggerClassName)}
          aria-label={t('common.enlargeImage', { label: alt })}
        >
          {children}
        </button>
      </DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/85 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content
          className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 max-w-[92vw] max-h-[92vh] focus:outline-hidden data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
          aria-describedby={undefined}
        >
          <DialogPrimitive.Title className="sr-only">{alt}</DialogPrimitive.Title>
          <img
            src={src}
            alt={alt}
            className="max-w-[92vw] max-h-[92vh] rounded-lg object-contain shadow-2xl"
          />
          <DialogPrimitive.Close
            className="absolute -right-3 -top-3 rounded-full bg-white text-slate-900 p-1.5 shadow-lg hover:bg-slate-100 focus:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
            aria-label={t('common.closeImage')}
          >
            <X className="w-4 h-4" />
          </DialogPrimitive.Close>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
