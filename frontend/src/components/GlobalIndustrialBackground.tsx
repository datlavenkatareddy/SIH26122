import React from 'react';
import industrialBg from '@/assets/industrial-bg.png';

interface GlobalIndustrialBackgroundProps {
  /**
   * 'hero' for Login full-page presentation, 'ambient' (default) for AppShell & dashboards
   */
  variant?: 'ambient' | 'hero';
}

export function GlobalIndustrialBackground({ variant = 'ambient' }: GlobalIndustrialBackgroundProps) {
  if (variant === 'hero') {
    return (
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        {/* Full-viewport background image spanning entire screen seamlessly */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-[0.88] dark:opacity-[0.45] transition-opacity duration-300"
          style={{ backgroundImage: `url(${industrialBg})` }}
        />
        {/* Dark Mode Overlay */}
        <div className="hidden dark:block absolute inset-0 bg-gradient-to-br from-[#061526]/92 via-[#071B2D]/85 to-[#0A2340]/88 transition-colors duration-200" />
        {/* Light Mode Overlay — Cool steel-slate atmospheric wash preserving natural industrial tones, mountains & sky */}
        <div className="block dark:hidden absolute inset-0 bg-gradient-to-r from-[#F1F5F9]/65 via-[#E2E8F0]/30 to-transparent transition-colors duration-200" />
        {/* Ambient atmospheric brand glow anchors (Orange glow scoped to Dark Mode only to prevent orange film in Light Mode) */}
        <div className="hidden dark:block absolute -top-24 -left-24 w-96 h-96 rounded-full opacity-25 bg-[#FF7A18] blur-3xl pointer-events-none" />
        <div className="block dark:hidden absolute -top-24 -left-24 w-96 h-96 rounded-full opacity-10 bg-[#0284C7] blur-3xl pointer-events-none" />
        <div className="absolute bottom-10 right-10 w-96 h-96 rounded-full opacity-10 dark:opacity-20 bg-[#14B8A6] blur-3xl pointer-events-none" />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* Full-viewport background image (visible across all dashboards and app pages) */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-[0.85] dark:opacity-[0.65] transition-opacity duration-300"
        style={{ backgroundImage: `url(${industrialBg})` }}
      />

      {/* Atmospheric Readability Overlays — Crystal clear light sky tone and rich dark navy atmosphere */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#F4F8FC]/30 via-transparent to-[#E2E8F0]/40 dark:from-[#06121E]/60 dark:via-[#071524]/45 dark:to-[#040C16]/65 transition-colors duration-200" />

      {/* Ambient glowing brand anchors */}
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full opacity-10 dark:opacity-20 bg-[#FF7A18] blur-3xl" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full opacity-10 dark:opacity-15 bg-[#14B8A6] blur-3xl" />
    </div>
  );
}

export default GlobalIndustrialBackground;
