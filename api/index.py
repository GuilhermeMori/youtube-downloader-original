# api/index.py - Vercel serverless function otimizada

import os
import sys
import re
import json
import random
import time
from urllib.parse import urlparse, parse_qs

# Add the parent directory to the Python path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
    import yt_dlp
    import requests
    
    # Criar aplicação Flask
    app = Flask(__name__, static_folder=os.path.join(parent_dir, 'static'))
    app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
    
    # Configurar CORS
    CORS(app)
    
    # Regex para validar URLs do YouTube
    YOUTUBE_URL_PATTERN = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
    )
    
    class ServerlessYouTubeExtractor:
        """Extrator otimizado para ambientes serverless"""
        
        def __init__(self):
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            ]
            
            self.referers = [
                'https://www.youtube.com/',
                'https://www.google.com/',
                'https://www.bing.com/',
                'https://duckduckgo.com/',
            ]
        
        def get_random_headers(self):
            """Gera headers aleatórios para simular diferentes navegadores"""
            user_agent = random.choice(self.user_agents)
            referer = random.choice(self.referers)
            
            is_mobile = any(mobile in user_agent.lower() for mobile in ['mobile', 'iphone', 'android'])
            
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': random.choice([
                    'en-US,en;q=0.9',
                    'pt-BR,pt;q=0.9,en;q=0.8',
                    'es-ES,es;q=0.9,en;q=0.8',
                ]),
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none' if 'google' in referer else 'cross-site',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Referer': referer,
            }
            
            if is_mobile:
                headers.update({
                    'Sec-Ch-Ua-Mobile': '?1',
                    'Sec-Ch-Ua-Platform': random.choice(['"Android"', '"iOS"', '"Windows"']),
                })
            else:
                headers.update({
                    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': random.choice(['"Windows"', '"macOS"', '"Linux"']),
                })
                
            return headers
        
        def get_ydl_opts(self, use_alternative_client=False):
            """Configurações do yt-dlp otimizadas para serverless"""
            headers = self.get_random_headers()
            
            opts = {
                'quiet': True,
                'no_warnings': True,
                'extractflat': False,
                'ignoreerrors': False,
                
                # Headers personalizados
                'http_headers': headers,
                'user_agent': headers['User-Agent'],
                'referer': headers['Referer'],
                
                # Configurações de rede otimizadas para serverless
                'socket_timeout': 30,
                'retries': 3,
                'fragment_retries': 3,
                'http_chunk_size': 1048576,  # 1MB chunks
                
                # Simula comportamento humano
                'sleep_interval': random.uniform(0.5, 2.0),
                'max_sleep_interval': 5,
                
                # Configurações específicas do YouTube
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls'],
                        'player_client': ['android', 'web', 'ios'] if use_alternative_client else ['web'],
                        'player_skip': ['webpage'],
                    }
                },
                
                # Evita detecção de bot
                'cookiefile': None,
                'cookiesfrombrowser': None,
                
                # Configurações de formato
                'format': 'best[height<=720]/best[height<=480]/best',
                'merge_output_format': 'mp4',
            }
            
            return opts
        
        def extract_video_id(self, url):
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
        
        def get_video_info_with_fallback(self, url):
            """Obtém informações do vídeo com múltiplas estratégias de fallback"""
            video_id = self.extract_video_id(url)
            if not video_id:
                raise Exception('URL do YouTube inválida')
            
            # Estratégia 1: Tentar com cliente web padrão
            for attempt in range(3):
                try:
                    opts = self.get_ydl_opts(use_alternative_client=False)
                    
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        return self._format_video_info(info)
                        
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    # Se detectou bloqueio, tenta estratégias alternativas
                    if any(keyword in error_msg for keyword in ['blocked', 'forbidden', '403', 'rate limit', 'too many requests']):
                        print(f"Tentativa {attempt + 1}: Bloqueio detectado, tentando estratégia alternativa...")
                        
                        if attempt < 2:
                            # Estratégia 2: Usar cliente alternativo
                            try:
                                opts = self.get_ydl_opts(use_alternative_client=True)
                                with yt_dlp.YoutubeDL(opts) as ydl:
                                    info = ydl.extract_info(url, download=False)
                                    return self._format_video_info(info)
                            except:
                                pass
                            
                            # Estratégia 3: Usar API não oficial como fallback
                            try:
                                fallback_info = self._get_fallback_info(video_id)
                                if fallback_info:
                                    return fallback_info
                            except:
                                pass
                            
                            # Espera antes da próxima tentativa
                            delay = min(1 * (2 ** attempt), 10)
                            time.sleep(delay + random.uniform(0, 1))
                            continue
                    
                    # Se é a última tentativa, relança o erro
                    if attempt == 2:
                        # Retorna informações básicas como fallback final
                        return self._get_minimal_info(video_id, url)
                    
                    # Espera antes da próxima tentativa
                    delay = min(1 * (2 ** attempt), 10)
                    time.sleep(delay + random.uniform(0, 1))
            
            # Fallback final
            return self._get_minimal_info(video_id, url)
        
        def _format_video_info(self, info):
            """Formata as informações do vídeo de forma consistente"""
            return {
                'success': True,
                'video_id': info.get('id', ''),
                'title': info.get('title', 'Título não disponível'),
                'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
                'duration': self._format_duration(info.get('duration', 0)),
                'uploader': info.get('uploader', 'Canal não identificado'),
                'view_count': self._format_number(info.get('view_count', 0)),
                'upload_date': self._format_date(info.get('upload_date')),
                'thumbnail': info.get('thumbnail', f'https://img.youtube.com/vi/{info.get("id", "")}/maxresdefault.jpg'),
                'youtube_url': info.get('webpage_url', ''),
                'direct_link': info.get('webpage_url', ''),
                'formats': self._extract_formats(info.get('formats', [])),
            }
        
        def _get_fallback_info(self, video_id):
            """Tenta obter informações básicas via API não oficial"""
            try:
                # Usa uma API pública para obter informações básicas
                api_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                
                headers = self.get_random_headers()
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
            
            return None
        
        def _get_minimal_info(self, video_id, url):
            """Retorna informações mínimas quando tudo mais falha"""
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
        
        def _extract_formats(self, formats):
            """Extrai formatos de vídeo disponíveis"""
            video_formats = []
            
            for fmt in formats:
                if fmt.get('vcodec') and fmt.get('vcodec') != 'none':
                    video_formats.append({
                        'format_id': fmt.get('format_id', ''),
                        'resolution': f"{fmt.get('height', 0)}p",
                        'ext': fmt.get('ext', ''),
                        'quality': fmt.get('format_note', ''),
                        'has_audio': fmt.get('acodec') and fmt.get('acodec') != 'none',
                        'filesize': fmt.get('filesize', 0)
                    })
            
            # Ordena por qualidade
            video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
            return video_formats[:10]  # Limita a 10 formatos
        
        def _format_duration(self, duration):
            """Formata duração em segundos para formato legível"""
            if not duration:
                return 'N/A'
            
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        
        def _format_number(self, number):
            """Formata números grandes de forma legível"""
            if not number:
                return 'N/A'
            
            if number >= 1_000_000:
                return f"{number/1_000_000:.1f}M"
            elif number >= 1_000:
                return f"{number/1_000:.1f}K"
            else:
                return str(number)
        
        def _format_date(self, date_str):
            """Formata data de upload"""
            if not date_str:
                return 'Data não disponível'
            
            try:
                # Formato YYYYMMDD
                if len(date_str) == 8:
                    year = date_str[:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    return f"{day}/{month}/{year}"
            except:
                pass
            
            return date_str
    
    # Instanciar o extrator
    extractor = ServerlessYouTubeExtractor()
    
    @app.route('/api/info', methods=['POST'])
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
            video_info = extractor.get_video_info_with_fallback(url)
            return jsonify(video_info), 200

        except Exception as e:
            print(f"Erro ao obter informações do vídeo: {e}")
            return jsonify({'error': 'Erro interno do servidor.'}), 500

    @app.route('/api/download', methods=['POST'])
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
            },
            'usage': {
                'info': {
                    'method': 'POST',
                    'body': {'url': 'https://www.youtube.com/watch?v=VIDEO_ID'},
                    'description': 'Obtém informações básicas do vídeo com anti-bloqueio'
                },
                'download': {
                    'method': 'POST',
                    'body': {'url': 'https://www.youtube.com/watch?v=VIDEO_ID', 'format_id': 'best'},
                    'description': 'Obtém informações para download'
                }
            }
        })
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "YouTube Downloader API is running!", 200

except ImportError as e:
    # Fallback se houver problemas com imports
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return jsonify({'error': f'Import error: {str(e)}', 'status': 'API is running but with limited functionality'})

# Exportar a aplicação para o Vercel
# O Vercel automaticamente detecta 'app' como a aplicação Flask