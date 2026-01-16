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


@logs_viewer_bp.route('/download', methods=['GET'])
@jwt_required
@role_required('admin')
def download_logs(current_user):
    """Download all logs as ZIP archive"""
    import zipfile
    import io
    from datetime import datetime
    from flask import send_file
    
    try:
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Get all log files
            log_files = {
                'app.log': os.path.join(Config.LOG_FOLDER, 'app.log'),
                'errors.log': os.path.join(Config.LOG_FOLDER, 'errors.log'),
                'bot.log': os.path.join(Config.LOG_FOLDER, 'bot.log'),
                'bot_errors.log': os.path.join(Config.LOG_FOLDER, 'bot_errors.log')
            }
            
            files_added = 0
            for log_filename, log_path in log_files.items():
                if os.path.exists(log_path):
                    try:
                        # Read file and add to ZIP
                        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            zip_file.writestr(log_filename, content)
                        files_added += 1
                        logger.info(f"Added {log_filename} to download archive")
                    except Exception as e:
                        logger.warning(f"Failed to add {log_filename} to archive: {e}")
        
        if files_added == 0:
            return jsonify({'error': 'No log files found'}), 404
        
        # Reset buffer position to beginning
        zip_buffer.seek(0)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'realty_logs_{timestamp}.zip'
        
        logger.info(f"Downloading logs archive: {filename} ({files_added} files)")
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error creating logs archive: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@logs_viewer_bp.route('/file/<log_type>', methods=['GET'])
@jwt_required
@role_required('admin')
def download_log_file(log_type, current_user):
    """Download specific log file"""
    from flask import send_file
    
    log_files = {
        'app': 'app.log',
        'errors': 'errors.log',
        'bot': 'bot.log',
        'bot_errors': 'bot_errors.log'
    }
    
    if log_type not in log_files:
        return jsonify({'error': f'Invalid log type. Allowed: {", ".join(log_files.keys())}'}), 400
    
    log_filename = log_files[log_type]
    log_path = os.path.join(Config.LOG_FOLDER, log_filename)
    
    if not os.path.exists(log_path):
        return jsonify({'error': f'Log file {log_filename} not found'}), 404
    
    try:
        logger.info(f"Downloading log file: {log_filename}")
        return send_file(
            log_path,
            mimetype='text/plain',
            as_attachment=True,
            download_name=log_filename
        )
    except Exception as e:
        logger.error(f"Error sending log file {log_filename}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500