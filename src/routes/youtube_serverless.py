# src/routes/youtube_serverless.py

import os
import re
from flask import Blueprint, request, jsonify
from ..utils.serverless_extractor import ServerlessYouTubeExtractor

youtube_bp = Blueprint('youtube_serverless_bp', __name__)

# Regex para validar diferentes formatos de URL do YouTube
YOUTUBE_URL_PATTERN = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
)

@youtube_bp.route('/info', methods=['POST'])
def get_video_info():
    """Get video information optimized for serverless environments"""
    if not request.is_json:
        return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL não fornecida.'}), 400
    
    if not YOUTUBE_URL_PATTERN.match(url):
        return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

    try:
        extractor = ServerlessYouTubeExtractor()
        video_info = extractor.get_video_info_with_fallback(url)
        
        return jsonify(video_info), 200

    except Exception as e:
        print(f"Erro ao obter informações do vídeo: {e}")
        return jsonify({'error': 'Erro interno do servidor.'}), 500

@youtube_bp.route('/download', methods=['POST'])
def download_video():
    """Download video optimized for serverless environments"""
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
        extractor = ServerlessYouTubeExtractor()
        
        # Para ambientes serverless, retornamos apenas o link direto
        # O download real seria feito pelo cliente
        video_info = extractor.get_video_info_with_fallback(url)
        
        if not video_info.get('success'):
            return jsonify({'error': 'Não foi possível obter informações do vídeo.'}), 500
        
        # Retorna informações para download no cliente
        return jsonify({
            'success': True,
            'video_id': video_info.get('video_id'),
            'title': video_info.get('title'),
            'direct_link': video_info.get('direct_link'),
            'youtube_url': video_info.get('youtube_url'),
            'thumbnail': video_info.get('thumbnail'),
            'formats': video_info.get('formats', []),
            'message': 'Para ambientes serverless, use o link direto para download'
        }), 200

    except Exception as e:
        print(f"Erro no download: {e}")
        return jsonify({'error': 'Erro interno do servidor.'}), 500

@youtube_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for serverless environments"""
    return jsonify({
        'status': 'healthy',
        'service': 'youtube-downloader-serverless',
        'version': '1.0.0'
    }), 200
