import Link from "next/link";
import type { ReactNode } from "react";

type ButtonLinkProps = {
  href: string;
  children: ReactNode;
  variant?: "primary" | "ghost" | "inline";
  external?: boolean;
};

export function ButtonLink({ href, children, variant = "primary", external }: ButtonLinkProps) {
  const className = `btn btn--${variant}`;
  if (external) {
    return (
      <a href={href} className={className} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
