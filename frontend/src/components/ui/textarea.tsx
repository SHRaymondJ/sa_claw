import * as React from 'react'

import { cn } from '@/lib/utils'

const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<'textarea'>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        'flex min-h-[104px] w-full border border-[var(--line)] bg-[var(--paper)] px-3 py-3 text-sm leading-6 text-[var(--ink)] outline-none placeholder:text-[var(--muted)] focus:border-[var(--line-strong)] transition-colors duration-200',
        className,
      )}
      {...props}
    />
  ),
)
Textarea.displayName = 'Textarea'

export { Textarea }
