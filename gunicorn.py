bind = "0.0.0.0:8999"

workers = 2
worker_class = "gthread"
threads = 4

timeout = 180
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"

preload_app = False