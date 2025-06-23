import multiprocessing

# Azure ML requires the container to bind to port 5001
bind = "0.0.0.0:5001"
backlog = 2048

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 60
keepalive = 5

# Restart workers periodically
max_requests = 1000
max_requests_jitter = 50

# Performance
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)

# Process naming
proc_name = "ml-model-api"

# Optional: Clean options for Azure ML environment
daemon = False
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
