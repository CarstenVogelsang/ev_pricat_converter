"""API Blueprint for file uploads.

Provides endpoints for uploading images to be used in Markdown content.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.services.storage_service import StorageService


api_upload_bp = Blueprint('api_upload', __name__, url_prefix='/api/upload')

# Shared storage service instance
_storage = None


def get_storage() -> StorageService:
    """Get or create storage service instance."""
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage


@api_upload_bp.route('/image', methods=['POST'])
@login_required
def upload_image():
    """Upload an image for Markdown content.

    Accepts multipart/form-data with a 'file' field containing the image.
    Images are validated, resized if necessary, and stored.

    Returns:
        JSON with 'url' (public URL) and 'markdown' (ready-to-use syntax)

    Example:
        curl -X POST http://localhost:5001/api/upload/image \
             -H "Cookie: session=..." \
             -F "file=@screenshot.png"

        Response:
        {
            "success": true,
            "url": "/static/uploads/markdown/20251230_160500_abc12345.png",
            "markdown": "![Bild](/static/uploads/markdown/20251230_160500_abc12345.png)"
        }
    """
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Keine Datei im Request'
        }), 400

    file = request.files['file']

    try:
        storage = get_storage()
        result = storage.upload_markdown_image(file)

        return jsonify({
            'success': True,
            'url': result['url'],
            'markdown': result['markdown'],
            'filename': result['filename']
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Upload fehlgeschlagen: {str(e)}'
        }), 500


@api_upload_bp.route('/image', methods=['DELETE'])
@login_required
def delete_image():
    """Delete a previously uploaded image.

    Request body (JSON):
        url: The URL of the image to delete

    Returns:
        JSON with success status
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({
            'success': False,
            'error': 'URL fehlt'
        }), 400

    try:
        storage = get_storage()
        deleted = storage.delete_markdown_image(data['url'])

        return jsonify({
            'success': deleted,
            'message': 'Bild gelöscht' if deleted else 'Bild nicht gefunden'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Löschen fehlgeschlagen: {str(e)}'
        }), 500
