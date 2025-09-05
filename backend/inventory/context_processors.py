# yourapp/context_processors.py

import os

def sentry_context_processor(request):
    """
    A custom context processor to expose specific environment variables to templates.
    """
    return {
        'SENTRY_DSN': os.environ.get('SENTRY_DSN', None),
    }