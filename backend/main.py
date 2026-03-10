"""
main.py — Application entrypoint.
Run with:  python main.py
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # threaded=True is required so multiple concurrent requests each get
    # their own thread — necessary for the per-slot locking to work correctly.
    app.run(host="0.0.0.0", port=8000, threaded=True, debug=False)