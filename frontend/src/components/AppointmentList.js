import React from 'react';
import { Button } from './ui/Button';
import './ui/Button.css';
import './AppointmentList.css';

function formatDate(dateStr) {
  var d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });
}

function AppointmentList({ appointments, onCancel, cancellingId }) {
  if (appointments.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📋</div>
        <p>No upcoming appointments.</p>
      </div>
    );
  }

  return (
    <div className="appointment-list">
      {appointments.map(function(appt) {
        var isConfirmed = appt.status === 'confirmed';

        return (
          <div key={appt.id} className="appointment-card">

            {/* Left colour bar — blue for confirmed, grey for cancelled */}
            <div className={'appt-bar' + (isConfirmed ? ' appt-bar-confirmed' : ' appt-bar-cancelled')} />

            <div className="appt-body">
              <div className="appt-info">

                {/* Name + status badge */}
                <div className="appt-top">
                  <span className="appt-name">{appt.customer_name}</span>
                  <span className={'badge ' + (isConfirmed ? 'badge-green' : 'badge-gray')}>
                    {appt.status}
                  </span>
                </div>

                {/* Date / time / email */}
                <div className="appt-meta">
                  <span>📅 {formatDate(appt.slot_date)}</span>
                  <span>🕐 {appt.start_time} – {appt.end_time}</span>
                  <span>✉️ {appt.customer_email}</span>
                </div>

                {/* Optional note */}
                {appt.note && (
                  <p className="appt-note">"{appt.note}"</p>
                )}

              </div>

              {/* shadcn Button for cancel */}
              {isConfirmed && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={function() { onCancel(appt.id); }}
                  disabled={cancellingId === appt.id}
                >
                  {cancellingId === appt.id ? 'Cancelling…' : 'Cancel'}
                </Button>
              )}
            </div>

          </div>
        );
      })}
    </div>
  );
}

export default AppointmentList;