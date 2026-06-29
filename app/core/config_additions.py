# Add these fields to your Settings class in app/core/config.py
# (inside the class, after the existing fields)

    # ── Exotel settings ──────────────────────────────────────────────────────
    exotel_account_sid: str = "saraban1"           # "saraban1"
    exotel_api_key: str = "7750dc05c003ef2f3052cffdf58093e26f1aa63be7cef128"               # API KEY from dashboard
    exotel_api_token: str = "ce3be095fde37ee66efea2e4eb6cbb8fc29c8d9b002c345c"             # API TOKEN (password) from dashboard
    exotel_caller_id: str = "04446973172"             # Your ExoPhone (+91XXXXXXXXXX)
    exotel_virtual_number: str = "04446973172"        # Same as caller_id (fallback)

    # Public URL for Exotel webhook callbacks
    # For local dev, set this to your ngrok URL: https://xxxx.ngrok-free.app
    backend_public_url: str = "http://localhost:8000"