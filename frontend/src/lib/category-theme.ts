// Color lives in icons, badges, and left-border accents -- never in a full
// card background wash. Flooding a whole surface with a tint is exactly the
// "AI template" tell; a colored icon chip + a thin accent border reads as
// designed instead, the way Figma/Linear color their category chips.
export const CATEGORY_THEME = {
  overview: {
    icon: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
    card: "border-l-2 border-l-violet-500/50",
    tab: "data-active:border-violet-500/40 data-active:bg-violet-500/10 data-active:text-violet-700 dark:data-active:text-violet-300",
  },
  breakdown: {
    icon: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    card: "border-l-2 border-l-blue-500/50",
    tab: "data-active:border-blue-500/40 data-active:bg-blue-500/10 data-active:text-blue-700 dark:data-active:text-blue-300",
  },
  coverLetter: {
    icon: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    card: "border-l-2 border-l-amber-500/50",
    tab: "data-active:border-amber-500/40 data-active:bg-amber-500/10 data-active:text-amber-700 dark:data-active:text-amber-300",
  },
  improvements: {
    icon: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    card: "border-l-2 border-l-emerald-500/50",
    tab: "data-active:border-emerald-500/40 data-active:bg-emerald-500/10 data-active:text-emerald-700 dark:data-active:text-emerald-300",
  },
} as const;

// Recruiter's three-round funnel: a hue progression on the badge/border only,
// not the whole row background -- advancing rounds still reads as leveling
// up without turning the list into a wall of tinted panels.
export const ROUND_THEME: Record<number, string> = {
  1: "border-l-2 border-l-slate-400/50",
  2: "border-l-2 border-l-violet-500/50",
  3: "border-l-2 border-l-fuchsia-500/50",
};

export const GRADIENT_CTA =
  "border-0 bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 text-white shadow-md shadow-violet-500/20 hover:shadow-lg hover:shadow-violet-500/30 hover:brightness-110";

export const GRADIENT_TEXT =
  "bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 bg-clip-text text-transparent";
