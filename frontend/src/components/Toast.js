import React, { useEffect } from 'react';
import './Toast.css';

function Toast({ toast, onDismiss }) {
  // Auto-dismiss after 4 seconds
  useEffect(function() {
    var timer = setTimeout(function() { onDismiss(toast.id); }, 4000);
    return function() { clearTimeout(timer); };
  }, [toast.id, onDismiss]);

  return (
    <div className={'toast toast-' + toast.variant}>
      <span className="toast-message">{toast.message}</span>
      <button
        className="toast-dismiss"
        onClick={function() { onDismiss(toast.id); }}
      >✕</button>
    </div>
  );
}

function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="toast-container">
      {toasts.map(function(t) {
        return <Toast key={t.id} toast={t} onDismiss={onDismiss} />;
      })}
    </div>
  );
}

export { ToastContainer };