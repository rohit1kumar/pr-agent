
# !/bin/bash
# start celery

celery -A app.tasks worker --loglevel=info