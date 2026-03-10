import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from './ui/Dialog';
import { Button } from './ui/Button';
import './ui/Button.css';
import './BookingModal.css';

function formatDate(dateStr) {
  var d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });
}

function BookingModal({ slot, onClose, onConfirm }) {
  var [name, setName]     = useState('');
  var [email, setEmail]   = useState('');
  var [note, setNote]     = useState('');
  var [errors, setErrors] = useState({});
  var [loading, setLoading] = useState(false);

  function validate() {
    var e = {};
    if (!name.trim())  e.name  = 'Name is required.';
    if (!email.trim()) e.email = 'Email is required.';
    else if (!/\S+@\S+\.\S+/.test(email)) e.email = 'Enter a valid email.';
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit() {
    if (!validate()) return;
    setLoading(true);
    try {
      await onConfirm(name.trim(), email.trim().toLowerCase(), note.trim());
      // reset on success — parent closes the modal
      setName(''); setEmail(''); setNote(''); setErrors({});
    } catch (err) {
      // parent shows toast, keep modal open
    } finally {
      setLoading(false);
    }
  }

  return (
    // open={!!slot} → modal is open whenever a slot is selected
    <Dialog open={!!slot} onOpenChange={function(open) { if (!open) onClose(); }}>
      <DialogContent>

        <DialogHeader>
          <DialogTitle>Book Appointment</DialogTitle>
          <DialogDescription>
            Fill in your details to confirm the slot below.
          </DialogDescription>
        </DialogHeader>

        {/* Selected slot summary */}
        {slot && (
          <div className="modal-slot-summary">
            <span>📅 {formatDate(slot.slot_date)}</span>
            <span>🕐 {slot.start_time} – {slot.end_time}</span>
          </div>
        )}

        {/* Form */}
        <div className="modal-form">

          <div className="form-group">
            <label className="form-label" htmlFor="name">Full Name</label>
            <input
              id="name"
              className={'form-input' + (errors.name ? ' input-error' : '')}
              placeholder="Jane Smith"
              value={name}
              onChange={function(e) { setName(e.target.value); }}
            />
            {errors.name && <p className="field-error">{errors.name}</p>}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              className={'form-input' + (errors.email ? ' input-error' : '')}
              placeholder="jane@example.com"
              value={email}
              onChange={function(e) { setEmail(e.target.value); }}
            />
            {errors.email && <p className="field-error">{errors.email}</p>}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="note">
              Note <span className="label-optional">(optional)</span>
            </label>
            <textarea
              id="note"
              className="form-textarea"
              placeholder="Anything we should know…"
              rows={2}
              value={note}
              onChange={function(e) { setNote(e.target.value); }}
            />
          </div>

        </div>

        {/* shadcn Button components in the footer */}
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="default" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Booking…' : 'Confirm Booking'}
          </Button>
        </DialogFooter>

      </DialogContent>
    </Dialog>
  );
}

export default BookingModal;