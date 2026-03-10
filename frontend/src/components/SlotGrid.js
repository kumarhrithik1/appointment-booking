import React from 'react';
import './SlotGrid.css';

// Group flat slot list into { "2026-03-10": [...], "2026-03-11": [...] }
function groupByDate(slots) {
  const groups = {};
  slots.forEach(function(slot) {
    if (!groups[slot.slot_date]) groups[slot.slot_date] = [];
    groups[slot.slot_date].push(slot);
  });
  return groups;
}

// "2026-03-10" → "Tuesday, Mar 10"
function formatDate(dateStr) {
  var d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
}

function isToday(dateStr) {
  return dateStr === new Date().toISOString().slice(0, 10);
}

function SlotGrid({ slots, onSelectSlot }) {
  if (slots.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🗓</div>
        <p>No available slots for the next 7 days.</p>
      </div>
    );
  }

  var groups = groupByDate(slots);
  var sortedDates = Object.keys(groups).sort();

  return (
    <div className="slot-grid-container">
      {sortedDates.map(function(date) {
        return (
          <div key={date} className="slot-day">

            {/* Day heading */}
            <div className="slot-day-header">
              <span className="slot-day-name">{formatDate(date)}</span>
              {isToday(date) && <span className="badge badge-blue">Today</span>}
              <span className="slot-day-count">({groups[date].length} slots)</span>
            </div>

            {/* Time slot buttons */}
            <div className="slots-row">
              {groups[date].map(function(slot) {
                return (
                  <button
                    key={slot.id}
                    className="slot-btn"
                    onClick={function() { onSelectSlot(slot); }}
                  >
                    <span className="slot-start">{slot.start_time}</span>
                    <span className="slot-end">{slot.end_time}</span>
                  </button>
                );
              })}
            </div>

          </div>
        );
      })}
    </div>
  );
}

export default SlotGrid;