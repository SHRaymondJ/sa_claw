import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from '@radix-ui/react-slot'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap border text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--line-strong)] disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'border-[var(--ink)] bg-[var(--ink)] text-[var(--paper)] hover:bg-[#222222]',
        secondary:
          'border-[var(--line)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--surface-strong)]',
        ghost: 'border-transparent bg-transparent text-[var(--muted)] hover:bg-[var(--surface)]',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
      },
    },
    defaultVariants: {
      variant: 'secondary',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
  },
)
Button.displayName = 'Button'

export { Button, buttonVariants }
