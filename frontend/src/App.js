import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './components/ui/Button';
import './components/ui/Button.css';
import SlotGrid from './components/SlotGrid';
import BookingModal from './components/BookingModal';
import AppointmentList from './components/AppointmentList';
import { ToastContainer } from './components/Toast';
import { api } from './api';
import './App.css';

// Simple toast manager — lives here so any action can trigger a notification
var nextToastId = 0;

function useToasts() {
  var [toasts, setToasts] = useState([]);

  var addToast = useCallback(function(message, variant) {
    var id = ++nextToastId;
    setToasts(function(prev) {
      return prev.concat({ id: id, message: message, variant: variant || 'info' });
    });
  }, []);

  var dismiss = useCallback(function(id) {
    setToasts(function(prev) { return prev.filter(function(t) { return t.id !== id; }); });
  }, []);

  return { toasts: toasts, addToast: addToast, dismiss: dismiss };
}

function App() {
  var [view, setView]               = useState('availability');
  var [slots, setSlots]             = useState([]);
  var [appointments, setAppointments] = useState([]);
  var [loading, setLoading]         = useState(false);
  var [selectedSlot, setSelectedSlot] = useState(null);
  var [cancellingId, setCancellingId] = useState(null);
  var toasts = useToasts();

  // --- Data loaders ---

  async function loadSlots() {
    setLoading(true);
    try {
      setSlots(await api.getSlots());
    } catch (err) {
      toasts.addToast('Failed to load slots. Is the backend running?', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function loadAppointments() {
    setLoading(true);
    try {
      setAppointments(await api.getAppointments());
    } catch (err) {
      toasts.addToast('Failed to load appointments.', 'error');
    } finally {
      setLoading(false);
    }
  }

  // Reload data whenever the tab changes
  useEffect(function() {
    if (view === 'availability') loadSlots();
    else loadAppointments();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  // --- Actions ---

  async function handleBook(name, email, note) {
    try {
      await api.bookAppointment(selectedSlot.id, name, email, note);
      toasts.addToast('Appointment confirmed for ' + selectedSlot.start_time + '!', 'success');
      setSelectedSlot(null);
      loadSlots();
    } catch (err) {
      toasts.addToast(err.message || 'Booking failed.', 'error');
      throw err; // re-throw so BookingModal stays open
    }
  }

  async function handleCancel(id) {
    setCancellingId(id);
    try {
      await api.cancelAppointment(id);
      toasts.addToast('Appointment cancelled.', 'info');
      loadAppointments();
    } catch (err) {
      toasts.addToast(err.message || 'Cancellation failed.', 'error');
    } finally {
      setCancellingId(null);
    }
  }

  var confirmedCount = appointments.filter(function(a) { return a.status === 'confirmed'; }).length;

  // --- Render ---

  return (
    <div className="app">

      {/* ---- Header ---- */}
      <header className="app-header">
        <div className="header-inner">

          <div className="header-logo">
            <div className="logo-icon">📅</div>
            BookSlot
          </div>

          {/* shadcn Button components used in the nav */}
          <nav className="header-nav">
            <Button
              variant={view === 'availability' ? 'default' : 'ghost'}
              size="sm"
              onClick={function() { setView('availability'); }}
            >
              🗓 Availability
            </Button>

            <Button
              variant={view === 'appointments' ? 'default' : 'ghost'}
              size="sm"
              onClick={function() { setView('appointments'); }}
            >
              📋 Appointments
              {confirmedCount > 0 && (
                <span className="nav-count">{confirmedCount}</span>
              )}
            </Button>
          </nav>

        </div>
      </header>

      {/* ---- Main ---- */}
      <main className="app-main">
        <div className="card">

          {/* Card header */}
          <div className="card-header">
            <div>
              <h2 className="card-title">
                {view === 'availability' ? 'Available Time Slots' : 'Your Appointments'}
              </h2>
              <p className="card-subtitle">
                {view === 'availability'
                  ? 'Click any slot to book a 30-minute appointment. Showing the next 7 days.'
                  : 'Manage your confirmed appointments below.'}
              </p>
            </div>

            {/* Refresh — shadcn Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={view === 'availability' ? loadSlots : loadAppointments}
              disabled={loading}
            >
              🔄
            </Button>
          </div>

          <div className="card-divider" />

          {/* Card body */}
          <div className="card-body">
            {loading ? (
              <div className="loading-state">Loading…</div>
            ) : view === 'availability' ? (
              <SlotGrid slots={slots} onSelectSlot={setSelectedSlot} />
            ) : (
              <AppointmentList
                appointments={appointments}
                onCancel={handleCancel}
                cancellingId={cancellingId}
              />
            )}
          </div>

        </div>
      </main>

      {/* ---- Booking modal (shadcn Dialog) ---- */}
      <BookingModal
        slot={selectedSlot}
        onClose={function() { setSelectedSlot(null); }}
        onConfirm={handleBook}
      />

      {/* ---- Toast notifications ---- */}
      <ToastContainer toasts={toasts.toasts} onDismiss={toasts.dismiss} />

    </div>
  );
}

export default App;