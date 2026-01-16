"""
Logs viewer routes - real-time log viewing
"""
import json
from flask import Blueprint, Response, request, jsonify, stream_with_context
from app.utils.decorators import jwt_required, role_required
import os
import time
import logging
from app.config import Config

logs_viewer_bp = Blueprint('logs_viewer', __name__)
logger = logging.getLogger(__name__)


@logs_viewer_bp.route('/stream', methods=['GET'])
def stream_logs():
    """Stream logs in real-time using Server-Sent Events"""
    # Check auth manually since EventSource doesn't support headers
    from app.utils.jwt import verify_token
    token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return Response(
            'data: {"error": "Unauthorized"}\n\n',
            mimetype='text/event-stream',
            status=401
        )
    
    try:
        payload = verify_token(token)
        from app.models.user import User
        user = User.query.get(payload.get('user_id'))
        if not user or user.web_role != 'admin':
            return Response(
                'data: {"error": "Forbidden"}\n\n',
                mimetype='text/event-stream',
                status=403
            )
    except Exception as e:
        logger.error(f"Auth error in stream_logs: {e}")
        return Response(
            'data: {"error": "Unauthorized"}\n\n',
            mimetype='text/event-stream',
            status=401
        )
    
    log_type = request.args.get('type', 'app')  # app, errors, bot
    lines = request.args.get('lines', 100, type=int)
    
    def generate():
        """Generate log lines"""
        log_files = {
            'app': os.path.join(Config.LOG_FOLDER, 'app.log'),
            'errors': os.path.join(Config.LOG_FOLDER, 'errors.log'),
            'bot': os.path.join(Config.LOG_FOLDER, 'bot.log'),
            'bot_errors': os.path.join(Config.LOG_FOLDER, 'bot_errors.log')
        }
        
        log_file = log_files.get(log_type)
        if not log_file or not os.path.exists(log_file):
            yield f"data: {json.dumps({'error': 'Log file not found'})}\n\n"
            return
        
        # Read last N lines
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last N lines
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                # Send initial lines
                for line in last_lines:
                    if line.strip():
                        yield f"data: {json.dumps({'line': line.rstrip()})}\n\n"
                
                # Stream new lines
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if line:
                        yield f"data: {json.dumps({'line': line.rstrip()})}\n\n"
                    else:
                        time.sleep(0.5)  # Wait for new content
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@logs_viewer_bp.route('/files', methods=['GET'])
@jwt_required
@role_required('admin')
def list_log_files(current_user):
    """List available log files"""
    log_files = []
    
    if os.path.exists(Config.LOG_FOLDER):
        for filename in os.listdir(Config.LOG_FOLDER):
            if filename.endswith('.log'):
                filepath = os.path.join(Config.LOG_FOLDER, filename)
                try:
                    stat = os.stat(filepath)
                    log_files.append({
                        'name': filename,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
                except Exception:
                    pass
    
    return jsonify({'files': log_files})


@logs_viewer_bp.route('/view', methods=['GET'])
@jwt_required
@role_required('admin')
def view_logs_page(current_user):
    """Logs viewer page"""
    from flask import render_template
    return render_template('logs_viewer.html')

