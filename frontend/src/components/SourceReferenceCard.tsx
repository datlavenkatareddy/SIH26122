import React, { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { FileText, ImageIcon, Hash, Loader2, Download } from 'lucide-react';
import { ExecutionEvent, SourceReference, claimsApi } from '@/api';
import { ImageLightbox } from '@/components/ImageLightbox';

export interface SourceReferenceCardProps {
  event: ExecutionEvent;
  sourceReferences?: SourceReference[];
  className?: string;
}

export function SourceReferenceCard({
  event,
  sourceReferences = [],
  className,
}: SourceReferenceCardProps) {
  const hasDocId = Boolean(event.document_id);
  const hasPhoto = Boolean(event.photo_path);
  const hasRefs = sourceReferences.length > 0;
  const isEvidenceAttached = hasPhoto || hasRefs || hasDocId;

  const filename = event.photo_path ? (event.photo_path.split(/[\/\\]/).pop() || 'evidence') : null;
  const isImage = event.photo_path ? /\.(jpg|jpeg|png|webp|gif|bmp)$/i.test(event.photo_path) : false;
  const isPdf = event.photo_path ? /\.pdf$/i.test(event.photo_path) : false;

  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState(false);

  useEffect(() => {
    // Contract: Do NOT call /claims/{eventId}/photo when photo_path is absent
    if (!hasPhoto) return;
    let cancelled = false;
    let objectUrl: string | null = null;
    setPhotoError(false);
    claimsApi
      .getPhotoBlobUrl(event.event_id)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setPhotoUrl(url);
      })
      .catch(() => {
        if (!cancelled) setPhotoError(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [event.event_id, hasPhoto]);

  return (
    <div
      className={cn(
        'p-3.5 rounded-xl bg-card-subtle border border-border space-y-2.5 text-xs',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-primary" />
          Source Evidence Context
        </span>
        <span
          className={cn(
            'text-[10px] font-mono font-medium px-2 py-0.5 rounded-full border',
            isEvidenceAttached
              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
              : 'bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-500/20'
          )}
        >
          {isEvidenceAttached ? 'Evidence attached' : 'No evidence attached'}
        </span>
      </div>

      <div className="space-y-2">
        {hasDocId && (
          <div className="flex items-center justify-between text-[11px] bg-card p-2 rounded-lg border border-border/60">
            <span className="text-muted-foreground flex items-center gap-1">
              <Hash className="w-3 h-3 text-muted-foreground" />
              Source Document:
            </span>
            <span className="font-mono font-bold text-foreground">
              {event.document_id}
            </span>
          </div>
        )}

        {hasPhoto ? (
          isImage ? (
            <div className="flex items-center justify-between text-[11px] bg-card p-2 rounded-lg border border-border/60">
              <span className="text-muted-foreground flex items-center gap-1">
                <ImageIcon className="w-3 h-3 text-accent" />
                Attached Photo:
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-accent truncate max-w-[140px]" title={filename || ''}>
                  {filename}
                </span>
                {photoError ? (
                  <span className="text-[10px] text-destructive">Failed to load</span>
                ) : photoUrl ? (
                  <ImageLightbox src={photoUrl} alt={`Evidence photo for claim ${event.event_id}`}>
                    <img
                      src={photoUrl}
                      alt={`Evidence photo thumbnail for claim ${event.event_id}`}
                      className="w-9 h-9 rounded-md object-cover border border-border hover:opacity-80 transition-opacity cursor-pointer"
                    />
                  </ImageLightbox>
                ) : (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between text-[11px] bg-card p-2 rounded-lg border border-border/60">
              <span className="text-muted-foreground flex items-center gap-1">
                <FileText className="w-3.5 h-3.5 text-primary" />
                Attached Document:
              </span>
              <div className="flex items-center gap-2">
                <div className="flex flex-col items-end">
                  <span className="font-mono font-bold text-foreground truncate max-w-[150px]" title={filename || ''}>
                    {filename}
                  </span>
                  <span className="text-[9px] text-emerald-600 dark:text-emerald-400 font-semibold uppercase">
                    {isPdf ? 'PDF Evidence' : 'Document Evidence'}
                  </span>
                </div>
                {photoUrl && (
                  <a
                    href={photoUrl}
                    download={filename || 'evidence.bin'}
                    className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                    title="Download document"
                  >
                    <Download className="w-3.5 h-3.5 text-primary" />
                  </a>
                )}
              </div>
            </div>
          )
        ) : (
          <div className="p-3 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 flex flex-col items-center justify-center text-center gap-1 my-1">
            <FileText className="w-5 h-5 text-slate-400 dark:text-slate-500 mb-0.5" />
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">File not uploaded</span>
            <span className="text-[10px] text-muted-foreground">No evidence file attached</span>
          </div>
        )}

        {hasRefs && (
          <div className="space-y-1.5 pt-1">
            {sourceReferences.map((ref) => (
              <div
                key={ref.reference_id}
                className="p-2 bg-card rounded-lg border border-border/60 space-y-1 text-[11px]"
              >
                <div className="flex items-center justify-between font-mono text-[10px] text-muted-foreground">
                  <span className="font-bold text-primary">{ref.file_name || 'Source File'}</span>
                  {ref.sheet_name && <span>Sheet: {ref.sheet_name}</span>}
                  {ref.row_cell_ref && <span>Ref: {ref.row_cell_ref}</span>}
                </div>
                {ref.raw_snippet && (
                  <p
                    className="text-foreground/90 font-mono text-[10px] bg-muted/40 p-1.5 rounded border border-border/40 truncate"
                    title={ref.raw_snippet}
                  >
                    "{ref.raw_snippet}"
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
