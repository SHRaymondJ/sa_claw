import * as React from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const Sheet = DialogPrimitive.Root
const SheetTrigger = DialogPrimitive.Trigger
const SheetClose = DialogPrimitive.Close
const SheetPortal = DialogPrimitive.Portal

const SheetOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      'fixed inset-0 z-50 bg-[rgba(23,18,13,0.42)] backdrop-blur-[3px] data-[state=open]:animate-[fade-in_220ms_ease-out] data-[state=closed]:animate-[fade-out_160ms_ease-in]',
      className,
    )}
    {...props}
  />
))
SheetOverlay.displayName = DialogPrimitive.Overlay.displayName

const sheetVariants = cva(
  'fixed z-50 border border-[var(--line)] bg-[linear-gradient(180deg,rgba(255,255,255,0.62),rgba(255,255,255,0)),var(--paper)] p-0 shadow-[var(--shadow-strong)]',
  {
  variants: {
    side: {
      right:
        'inset-y-0 right-0 h-full w-[92vw] max-w-[420px] data-[state=open]:animate-[slide-left_260ms_cubic-bezier(0.22,1,0.36,1)] data-[state=closed]:animate-[slide-right_180ms_ease-in]',
      bottom:
        'inset-x-0 bottom-0 h-[80vh] w-full data-[state=open]:animate-[slide-up_260ms_cubic-bezier(0.22,1,0.36,1)] data-[state=closed]:animate-[slide-down_180ms_ease-in]',
    },
  },
  defaultVariants: {
    side: 'right',
  },
})

const SheetContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & VariantProps<typeof sheetVariants>
>(({ className, children, side = 'right', ...props }, ref) => (
  <SheetPortal>
    <SheetOverlay />
    <DialogPrimitive.Content ref={ref} className={cn(sheetVariants({ side }), className)} {...props}>
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 border border-[var(--line)] p-2 text-[var(--muted)] transition-colors hover:bg-[var(--surface)]">
        <X className="h-4 w-4" />
        <span className="sr-only">关闭</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </SheetPortal>
))
SheetContent.displayName = DialogPrimitive.Content.displayName

const SheetHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex flex-col gap-2 border-b border-[var(--line)] px-5 py-4', className)} {...props} />
)

const SheetTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title ref={ref} className={cn('text-base font-semibold text-[var(--ink)]', className)} {...props} />
))
SheetTitle.displayName = DialogPrimitive.Title.displayName

const SheetDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description ref={ref} className={cn('text-sm leading-6 text-[var(--muted)]', className)} {...props} />
))
SheetDescription.displayName = DialogPrimitive.Description.displayName

export {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetPortal,
  SheetTitle,
  SheetTrigger,
}
