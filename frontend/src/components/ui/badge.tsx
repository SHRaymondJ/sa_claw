import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center border px-2 py-1 text-[11px] font-medium uppercase tracking-[0.16em]', {
  variants: {
    variant: {
      default: 'border-[var(--line)] bg-[var(--surface)] text-[var(--muted)]',
      dark: 'border-[var(--ink)] bg-[var(--ink)] text-[var(--paper)]',
      accent: 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--ink)]',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

function Badge({ className, variant, ...props }: React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof badgeVariants>) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
