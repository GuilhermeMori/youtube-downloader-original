# api/index.py - Vercel serverless function otimizada e simplificada

import os
import sys
import re
import json
import random
import time

# Add the parent directory to the Python path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    import yt_dlp
    import requests
    
    # Criar aplicação Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
    
    # Configurar CORS
    CORS(app)
    
    # Regex para validar URLs do YouTube
    YOUTUBE_URL_PATTERN = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
    )
    
    def get_random_headers():
        """Gera headers aleatórios para simular diferentes navegadores"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        ]
        
        referers = [
            'https://www.youtube.com/',
            'https://www.google.com/',
            'https://www.bing.com/',
        ]
        
        user_agent = random.choice(user_agents)
        referer = random.choice(referers)
        
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': referer,
        }
    
    def extract_video_id(url):
        """Extrai o ID do vídeo da URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def format_duration(seconds):
        """Formata duração em segundos para formato legível"""
        if not seconds:
            return 'N/A'
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def format_number(number):
        """Formata números grandes de forma legível"""
        if not number:
            return 'N/A'
        
        if number >= 1_000_000:
            return f"{number/1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number/1_000:.1f}K"
        else:
            return str(number)
    
    def get_video_info_with_fallback(url):
        """Obtém informações do vídeo com múltiplas estratégias de fallback"""
        video_id = extract_video_id(url)
        if not video_id:
            raise Exception('URL do YouTube inválida')
        
        # Estratégia 1: Tentar com yt-dlp simples
        for attempt in range(3):
            try:
                headers = get_random_headers()
                
                opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extractflat': False,
                    'ignoreerrors': False,
                    'http_headers': headers,
                    'user_agent': headers['User-Agent'],
                    'referer': headers['Referer'],
                    'socket_timeout': 30,
                    'retries': 2,
                    'fragment_retries': 2,
                    'sleep_interval': random.uniform(0.5, 2.0),
                    'max_sleep_interval': 5,
                    'extractor_args': {
                        'youtube': {
                            'skip': ['dash', 'hls'],
                            'player_client': ['web', 'android'],
                        }
                    },
                    'cookiefile': None,
                    'cookiesfrombrowser': None,
                }
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    return {
                        'success': True,
                        'video_id': info.get('id', video_id),
                        'title': info.get('title', f'Vídeo YouTube (ID: {video_id})'),
                        'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
                        'duration': format_duration(info.get('duration', 0)),
                        'uploader': info.get('uploader', 'Canal não identificado'),
                        'view_count': format_number(info.get('view_count', 0)),
                        'upload_date': info.get('upload_date', 'Data não disponível'),
                        'thumbnail': info.get('thumbnail', f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'),
                        'youtube_url': info.get('webpage_url', url),
                        'direct_link': info.get('webpage_url', url),
                        'formats': []
                    }
                    
            except Exception as e:
                error_msg = str(e).lower()
                print(f"Tentativa {attempt + 1}: {error_msg}")
                
                if any(keyword in error_msg for keyword in ['blocked', 'forbidden', '403', 'rate limit', 'too many requests']):
                    if attempt < 2:
                        time.sleep(random.uniform(1, 3))
                        continue
                
                # Se é a última tentativa, tenta fallback
                if attempt == 2:
                    break
                
                time.sleep(random.uniform(1, 2))
        
        # Estratégia 2: API não oficial
        try:
            api_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            headers = get_random_headers()
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'video_id': video_id,
                    'title': data.get('title', f'Vídeo YouTube (ID: {video_id})'),
                    'description': 'Informações não disponíveis devido a restrições do YouTube.',
                    'duration': 'N/A',
                    'uploader': 'Canal não identificado',
                    'view_count': 'N/A',
                    'upload_date': 'Data não disponível',
                    'thumbnail': data.get('thumbnail_url', f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'),
                    'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
                    'direct_link': f'https://www.youtube.com/watch?v={video_id}',
                    'warning': 'Informações limitadas - YouTube bloqueou acesso detalhado',
                    'formats': []
                }
        except Exception as e:
            print(f"Erro no fallback API: {e}")
        
        # Fallback final: informações mínimas
        return {
            'success': True,
            'video_id': video_id,
            'title': f'Vídeo YouTube (ID: {video_id})',
            'description': 'Informações não disponíveis devido a restrições do YouTube. Use o link direto para acessar o vídeo.',
            'duration': 'N/A',
            'uploader': 'Canal não identificado',
            'view_count': 'N/A',
            'upload_date': 'Data não disponível',
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            'youtube_url': url,
            'direct_link': url,
            'warning': 'Informações limitadas - YouTube bloqueou acesso detalhado',
            'formats': []
        }
    
    @app.route('/api/info', methods=['POST'])
    def get_video_info():
        """Get video information optimized for serverless environments"""
        try:
            if not request.is_json:
                return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

            data = request.get_json()
            url = data.get('url')

            if not url:
                return jsonify({'error': 'URL não fornecida.'}), 400
            
            if not YOUTUBE_URL_PATTERN.match(url):
                return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

            video_info = get_video_info_with_fallback(url)
            return jsonify(video_info), 200

        except Exception as e:
            print(f"Erro ao obter informações do vídeo: {e}")
            return jsonify({'error': 'Erro interno do servidor.'}), 500

    @app.route('/api/download', methods=['POST'])
    def download_video():
        """Download video optimized for serverless environments"""
        try:
            if not request.is_json:
                return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

            data = request.get_json()
            url = data.get('url')

            if not url:
                return jsonify({'error': 'URL não fornecida.'}), 400
            
            if not YOUTUBE_URL_PATTERN.match(url):
                return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

            video_info = get_video_info_with_fallback(url)
            
            if not video_info.get('success'):
                return jsonify({'error': 'Não foi possível obter informações do vídeo.'}), 500
            
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

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint for serverless environments"""
        return jsonify({
            'status': 'healthy',
            'service': 'youtube-downloader-serverless',
            'version': '1.0.0'
        }), 200

    @app.route('/api/test', methods=['GET'])
    def test_api():
        """Endpoint de teste para verificar se a API está funcionando"""
        return jsonify({
            'success': True,
            'message': 'YouTube Downloader API está funcionando!',
            'version': '2.1.0',
            'status': 'online',
            'endpoints': {
                'info': '/api/info (POST) - Obter informações do vídeo',
                'download': '/api/download (POST) - Download de vídeo',
                'health': '/api/health (GET) - Health check',
                'test': '/api/test (GET) - Testar API'
            }
        })
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        return jsonify({
            'message': 'YouTube Downloader API is running!',
            'version': '2.1.0',
            'status': 'online',
            'endpoints': ['/api/info', '/api/download', '/api/health', '/api/test']
        })

except ImportError as e:
    # Fallback se houver problemas com imports
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return jsonify({
            'error': f'Import error: {str(e)}', 
            'status': 'API is running but with limited functionality'
        })

# Exportar a aplicação para o Vercel