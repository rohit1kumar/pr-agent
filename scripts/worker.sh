#!/bin/bash

celery -A app.tasks worker --loglevel=info --concurrency=2 --max-memory-per-child=12000