// shadcn/ui — Button
// Uses class-variance-authority to define variants.
// Styles are written as plain className strings — no Tailwind config needed,
// they work as regular CSS class names that we define in Button.css.

import React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva } from 'class-variance-authority';
import { clsx } from 'clsx';

// cva generates a className string based on which variant + size is chosen
const buttonVariants = cva('btn', {
  variants: {
    variant: {
      default:     'btn-primary',
      outline:     'btn-outline',
      ghost:       'btn-ghost',
      destructive: 'btn-destructive',
      secondary:   'btn-secondary',
    },
    size: {
      default: 'btn-md',
      sm:      'btn-sm',
      lg:      'btn-lg',
      icon:    'btn-icon',
    },
  },
  defaultVariants: {
    variant: 'default',
    size: 'default',
  },
});

function Button({ className, variant, size, asChild = false, ...props }) {
  // asChild lets you render button styles on a different element (e.g. <a>)
  const Comp = asChild ? Slot : 'button';
  return (
    <Comp
      className={clsx(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export { Button };