import type { ReactNode } from "react";

type ProseProps = { children: ReactNode; as?: "div" | "section"; className?: string };

export function Prose({ children, as: Tag = "div", className }: ProseProps) {
  const cls = ["prose", className].filter(Boolean).join(" ");
  return <Tag className={cls}>{children}</Tag>;
}
