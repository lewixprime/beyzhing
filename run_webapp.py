# run_webapp.py
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "webapp.app:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
