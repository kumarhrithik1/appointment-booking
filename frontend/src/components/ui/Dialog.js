// shadcn/ui — Dialog
// Backed by @radix-ui/react-dialog which gives us:
//   - Focus trapping inside the modal
//   - Escape key to close
//   - aria-modal, role="dialog" for accessibility
// We style it with Dialog.css (plain CSS).

import React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import './Dialog.css';

// Re-export Root and Trigger unchanged
const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;

// Dark backdrop
function DialogOverlay() {
  return <DialogPrimitive.Overlay className="dialog-overlay" />;
}

// The white box that contains the content
function DialogContent({ children, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Content className="dialog-content" {...props}>
        {children}
        {/* X button — Radix wires up the close behaviour automatically */}
        <DialogPrimitive.Close className="dialog-close">✕</DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

function DialogHeader({ children }) {
  return <div className="dialog-header">{children}</div>;
}

function DialogTitle({ children }) {
  return (
    <DialogPrimitive.Title className="dialog-title">{children}</DialogPrimitive.Title>
  );
}

function DialogDescription({ children }) {
  return (
    <DialogPrimitive.Description className="dialog-description">
      {children}
    </DialogPrimitive.Description>
  );
}

function DialogFooter({ children }) {
  return <div className="dialog-footer">{children}</div>;
}

export { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter };