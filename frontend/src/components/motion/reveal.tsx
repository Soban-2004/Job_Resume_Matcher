"use client";

import { motion, type Variants } from "motion/react";
import type { ReactNode } from "react";

const containerVariants: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.07, delayChildren: 0.02 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 10, filter: "blur(4px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { type: "spring", stiffness: 320, damping: 30 },
  },
};

/** Wrap a list of `StaggerItem`s to have them reveal one after another
 * instead of popping in together -- used for requirement lists, candidate
 * rows, and anywhere else a set of similar items mounts at once. */
export function StaggerGroup({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div className={className} variants={containerVariants} initial="hidden" animate="show">
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div className={className} variants={itemVariants}>
      {children}
    </motion.div>
  );
}

/** Blur-fade entrance for a whole section (e.g. the results panel appearing
 * once a job completes) -- softer than a hard opacity pop. */
export function BlurFadeIn({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12, filter: "blur(8px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ type: "spring", stiffness: 280, damping: 30, delay }}
    >
      {children}
    </motion.div>
  );
}
