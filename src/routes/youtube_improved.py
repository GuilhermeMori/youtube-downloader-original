# src/routes/youtube_improved.py

import os
import re
import atexit
import shutil
import mimetypes
import tempfile
from flask import Blueprint, request, jsonify, Response
from src.utils.youtube_extractor import AntiDetectionYouTubeExtractor

youtube_improved_bp = Blueprint('youtube_improved_bp', __name__)

# Diretório temporário para processos de download
downloads_dir = tempfile.mkdtemp(prefix='youtube_downloader_improved_')

# Instância do extrator com anti-detecção
extractor = AntiDetectionYouTubeExtractor()

# Função para limpar arquivos temporários ao sair
def cleanup_temp_files():
    if os.path.exists(downloads_dir):
        shutil.rmtree(downloads_dir, ignore_errors=True)

# Registra a função de limpeza para ser executada ao sair
atexit.register(cleanup_temp_files)

# Regex para validar diferentes formatos de URL do YouTube
YOUTUBE_URL_PATTERN = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
)

@youtube_improved_bp.route('/info-improved', methods=['POST'])
def get_video_info_improved():
    """Get video information with anti-detection measures"""
    if not request.is_json:
        return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL não fornecida.'}), 400
    
    if not YOUTUBE_URL_PATTERN.match(url):
        return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

    try:
        # Usa o extrator com anti-detecção
        info_dict = extractor.extract_info_with_retry(url, download=False, use_proxy=True)
        
        if not info_dict:
            return jsonify({'error': 'Não foi possível obter informações do vídeo.'}), 500
        
        # Processa formatos disponíveis
        formats = info_dict.get('formats', [])
        video_formats = []
        
        # Formatos prioritários
        priority_formats = {
            '22': '720p MP4 (com áudio)',
            '18': '360p MP4 (com áudio)',
            '136': '720p MP4',
            '137': '1080p MP4', 
            '299': '1080p60 MP4',
            '298': '720p60 MP4',
            '247': '720p WebM',
            '248': '1080p WebM',
            '303': '1080p60 WebM',
            '302': '720p60 WebM'
        }
        
        # Separa formatos com e sem áudio
        combined_formats = []
        video_only_formats = []
        
        for fmt in formats:
            vcodec = fmt.get('vcodec')
            acodec = fmt.get('acodec')
            height = fmt.get('height')
            width = fmt.get('width')
            ext = fmt.get('ext')
            format_id = fmt.get('format_id')
            format_note = fmt.get('format_note', '')
            filesize = fmt.get('filesize')
            fps = fmt.get('fps')
            
            # Formatos com vídeo E áudio
            if (vcodec and vcodec != 'none' and 
                acodec and acodec != 'none' and 
                height and ext and format_id and height >= 360):
                
                quality_label = priority_formats.get(format_id, f"{height}p")
                if fps and fps > 30:
                    quality_label += f" {int(fps)}fps"
                quality_label += " (com áudio)"
                
                combined_formats.append({
                    'format_id': format_id,
                    'resolution': f"{height}p",
                    'quality_label': quality_label,
                    'ext': ext,
                    'height': height,
                    'width': width,
                    'vcodec': vcodec,
                    'acodec': acodec,
                    'format_note': format_note,
                    'filesize': filesize,
                    'fps': fps,
                    'has_audio': True
                })
            
            # Formatos apenas com vídeo
            elif (vcodec and vcodec != 'none' and 
                  (acodec == 'none' or acodec is None) and 
                  height and ext and format_id and height >= 720):
                
                quality_label = priority_formats.get(format_id, f"{height}p")
                if fps and fps > 30:
                    quality_label += f" {int(fps)}fps"
                
                # Adiciona informação sobre codec
                codec_info = ""
                if 'avc1' in vcodec or 'h264' in vcodec:
                    codec_info = " (H.264)"
                elif 'vp9' in vcodec:
                    codec_info = " (VP9)"
                elif 'av01' in vcodec:
                    codec_info = " (AV1)"
                
                video_only_formats.append({
                    'format_id': format_id,
                    'resolution': f"{height}p",
                    'quality_label': quality_label + codec_info + " (sem áudio)",
                    'ext': ext,
                    'height': height,
                    'width': width,
                    'vcodec': vcodec,
                    'format_note': format_note,
                    'filesize': filesize,
                    'fps': fps,
                    'has_audio': False
                })
        
        # Combina os formatos
        video_formats = combined_formats + video_only_formats
        
        # Remove duplicatas e ordena
        seen = {}
        unique_formats = []
        
        for fmt in video_formats:
            key = (fmt['height'], fmt['ext'])
            if key not in seen:
                seen[key] = fmt
                unique_formats.append(fmt)
            else:
                # Mantém o melhor codec
                existing = seen[key]
                current_vcodec = fmt['vcodec'].lower()
                existing_vcodec = existing['vcodec'].lower()
                
                if ('avc1' in current_vcodec or 'h264' in current_vcodec) and not ('avc1' in existing_vcodec or 'h264' in existing_vcodec):
                    seen[key] = fmt
                    unique_formats = [f for f in unique_formats if not (f['height'] == fmt['height'] and f['ext'] == fmt['ext'])]
                    unique_formats.append(fmt)
        
        # Ordena por altura e codec
        def sort_key(fmt):
            height = fmt['height']
            vcodec = fmt['vcodec'].lower()
            codec_priority = 0 if ('avc1' in vcodec or 'h264' in vcodec) else (1 if 'vp9' in vcodec else (2 if 'av01' in vcodec else 3))
            return (-height, codec_priority)
        
        unique_formats.sort(key=sort_key)
        
        # Filtra qualidades 360p e acima
        high_quality_formats = [fmt for fmt in unique_formats if fmt['height'] >= 360]
        high_quality_formats.sort(key=lambda x: (not x.get('has_audio', False), -x['height']))
        
        return jsonify({
            'title': info_dict.get('title', 'Título não disponível'),
            'duration': info_dict.get('duration', 0),
            'uploader': info_dict.get('uploader', 'Desconhecido'),
            'view_count': info_dict.get('view_count', 0),
            'description': info_dict.get('description', '')[:200] + '...' if info_dict.get('description') else '',
            'formats': high_quality_formats[:10],
            'anti_detection': True  # Indica que foi usado anti-detecção
        }), 200

    except Exception as e:
        error_message = str(e)
        if 'privado' in error_message.lower():
            return jsonify({'error': 'Este vídeo é privado e não pode ser acessado.'}), 403
        if 'não está disponível' in error_message.lower():
            return jsonify({'error': 'Este vídeo não está disponível.'}), 404
        
        return jsonify({'error': f'Erro ao obter informações: {error_message}'}), 500

@youtube_improved_bp.route('/download-improved', methods=['POST'])
def download_video_improved():
    """Download video with anti-detection measures"""
    if not request.is_json:
        return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

    data = request.get_json()
    url = data.get('url')
    format_id = data.get('format_id')

    if not url:
        return jsonify({'error': 'URL não fornecida.'}), 400
    
    if not YOUTUBE_URL_PATTERN.match(url):
        return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

    try:
        # Primeiro, obtém informações do vídeo
        info_dict = extractor.extract_info_with_retry(url, download=False, use_proxy=True)
        
        if not info_dict:
            return jsonify({'error': 'Não foi possível obter informações do vídeo.'}), 500
        
        # Verifica se o formato solicitado existe
        if format_id:
            formats = info_dict.get('formats', [])
            format_exists = any(fmt.get('format_id') == format_id for fmt in formats)
            
            if not format_exists:
                available_ids = [f.get('format_id') for f in formats if f.get('format_id')]
                return jsonify({
                    'error': f'Formato {format_id} não disponível para este vídeo.',
                    'available_formats': available_ids
                }), 400
        
        # Executa o download com anti-detecção
        final_filename = extractor.download_with_anti_detection(
            url=url,
            format_id=format_id,
            output_dir=downloads_dir
        )
        
        # Verifica se o arquivo foi criado
        if os.path.exists(final_filename):
            file_size = os.path.getsize(final_filename)
            
            # Limpa o nome do arquivo
            safe_filename = re.sub(r'[^\\w\\-_\\.]', '_', info_dict.get('title', 'video'))
            safe_filename = safe_filename[:100]
            file_extension = os.path.basename(final_filename).split('.')[-1]
            download_filename = f"{safe_filename}.{file_extension}"
            
            # Determina o tipo MIME
            mimetype = mimetypes.guess_type(final_filename)[0] or 'application/octet-stream'
            
            def generate():
                try:
                    with open(final_filename, 'rb') as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            yield chunk
                finally:
                    # Remove o arquivo após o streaming
                    try:
                        if os.path.exists(final_filename):
                            os.remove(final_filename)
                    except:
                        pass
            
            # Cria resposta de streaming
            response = Response(
                generate(),
                mimetype=mimetype,
                headers={
                    'Content-Disposition': f'attachment; filename="{download_filename}"',
                    'Content-Length': str(file_size),
                    'Content-Type': mimetype,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'X-Anti-Detection': 'enabled'  # Header personalizado
                }
            )
            
            return response
        else:
            return jsonify({'error': 'Arquivo não foi criado durante o download.'}), 500

    except Exception as e:
        error_message = str(e)
        if 'privado' in error_message.lower():
            return jsonify({'error': 'Este vídeo é privado e não pode ser acessado.'}), 403
        if 'não está disponível' in error_message.lower():
            return jsonify({'error': 'Este vídeo não está disponível.'}), 404
        
        return jsonify({'error': f'Erro no download: {error_message}'}), 500

@youtube_improved_bp.route('/health-check', methods=['GET'])
def health_check():
    """Endpoint para verificar se o serviço está funcionando"""
    return jsonify({
        'status': 'ok',
        'anti_detection': 'enabled',
        'proxy_support': 'enabled',
        'user_agent_rotation': 'enabled'
    }), 200

