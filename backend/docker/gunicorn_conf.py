import multiprocessing
import os
bind = "unix:/run/gunicorn.sock"
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
timeout = int(os.getenv("GUNICORN_TIMEOUT", 60))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 30))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
