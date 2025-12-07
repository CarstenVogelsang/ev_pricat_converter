"""Routes for Content Generator module."""

from flask import Blueprint, render_template
from flask_login import login_required

content_generator_bp = Blueprint(
    'content_generator',
    __name__,
    url_prefix='/content-generator'
)


@content_generator_bp.route('/')
@login_required
def index():
    """Display the Content Generator dashboard."""
    return render_template('content_generator/index.html')
