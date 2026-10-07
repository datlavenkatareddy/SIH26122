/**
 * WBS Explorer Page — Feature 30A (Stage 7)
 *
 * Thin page wrapper around WBSActivityExplorer.
 * Read-only reference view of schedule activities grouped by WBS code.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { FolderTree } from 'lucide-react';
import WBSActivityExplorer from '@/components/WBSActivityExplorer';

export default function WBSExplorerPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-300 dark:border-[#214766]/60 pb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-[#071A2D] dark:text-[#F5F7FA] tracking-tight flex items-center gap-2.5">
            <div className="p-1.5 rounded-xl bg-orange-50 dark:bg-orange-950/60 border border-orange-300 dark:border-orange-800/60 shadow-xs">
              <FolderTree className="w-5 h-5 text-[#FF7A18] dark:text-[#FF941F]" />
            </div>
            {t('wbs.title')}
          </h1>
          <p className="text-[#334155] dark:text-[#CBD5E1] text-xs font-semibold mt-1">
            {t('wbs.subtitle')}
          </p>
        </div>
      </div>

      <WBSActivityExplorer />
    </div>
  );
}
