import os

# Limit CPU threads and disable heavy secondary cross-encoder to stay well within 512MB RAM free tier
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["DISABLE_CROSS_ENCODER"] = "true"

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"[InsightForge] Starting Uvicorn on 0.0.0.0:{port}...")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, log_level="info", workers=1)
