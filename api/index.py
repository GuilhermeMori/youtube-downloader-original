import os
import sys
import tempfile
import shutil
import atexit
import re
import mimetypes
import json
import urllib.request
import urllib.parse

# Adicionar o diretório raiz ao path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from flask import Flask, request, jsonify, send_from_directory, Response, Blueprint
    from flask_cors import CORS
    import yt_dlp
    
    # Criar aplicação Flask
    app = Flask(__name__, static_folder=os.path.join(parent_dir, 'static'))
    app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
    
    # Configurar CORS
    CORS(app)
    
    # Diretório temporário para processar downloads
    downloads_dir = tempfile.mkdtemp(prefix='youtube_downloader_')
    
    # Função para limpar arquivos temporários
    def cleanup_temp_files():
        if os.path.exists(downloads_dir):
            shutil.rmtree(downloads_dir, ignore_errors=True)
    
    atexit.register(cleanup_temp_files)
    
    # Regex para validar URLs do YouTube
    YOUTUBE_URL_PATTERN = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
    )
    
    def extract_video_data_from_html(video_id):
        """Extrair dados do vídeo usando web scraping do YouTube"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            # Extrair dados do JSON-LD ou meta tags
            title = "Título não disponível"
            description = "Descrição não disponível"
            uploader = "Canal não identificado"
            duration = 0
            view_count = 0
            upload_date = "Data não disponível"
            
            # Tentar extrair do JSON-LD
            json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            json_matches = re.findall(json_ld_pattern, html, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    if isinstance(data, dict) and data.get('@type') == 'VideoObject':
                        title = data.get('name', title)
                        description = data.get('description', description)
                        uploader = data.get('author', {}).get('name', uploader)
                        duration = data.get('duration', duration)
                        upload_date = data.get('uploadDate', upload_date)
                        break
                except:
                    continue
            
            # Tentar extrair do meta tags se JSON-LD falhar
            if title == "Título não disponível":
                title_match = re.search(r'<title>([^<]+)</title>', html)
                if title_match:
                    title = title_match.group(1).replace(' - YouTube', '').strip()
            
            # Extrair visualizações
            view_patterns = [
                r'"viewCount":"(\d+)"',
                r'"view_count":"(\d+)"',
                r'(\d+(?:,\d+)*)\s*visualizações',
                r'(\d+(?:,\d+)*)\s*views'
            ]
            
            for pattern in view_patterns:
                view_match = re.search(pattern, html)
                if view_match:
                    view_count = int(view_match.group(1).replace(',', ''))
                    break
            
            # Extrair canal
            channel_patterns = [
                r'"ownerText":\{"runs":\[\{"text":"([^"]+)"',
                r'"channelName":"([^"]+)"',
                r'"author":"([^"]+)"'
            ]
            
            for pattern in channel_patterns:
                channel_match = re.search(pattern, html)
                if channel_match:
                    uploader = channel_match.group(1)
                    break
            
            return {
                'title': title,
                'description': description[:500] + ('...' if len(description) > 500 else ''),
                'uploader': uploader,
                'duration': duration,
                'view_count': view_count,
                'upload_date': upload_date,
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
            }
            
        except Exception as e:
            print(f"Erro no web scraping: {e}")
            return None
    
    @app.route('/api/info', methods=['POST'])
    def get_video_info():
        """Get video information without downloading"""
        if not request.is_json:
            return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL não fornecida.'}), 400
        
        if not YOUTUBE_URL_PATTERN.match(url):
            return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

        try:
            # Configurações otimizadas para Vercel/serverless
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': True,
                'no_check_certificate': True,
                'extract_retries': 3,
                'fragment_retries': 3,
                'retries': 3,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash'],
                        'player_skip': ['configs', 'webpage'],
                        'player_client': ['android', 'web'],
                    }
                },
                'cookiesfrombrowser': None,  # Não usar cookies
                'geo_bypass': True,
                'geo_bypass_country': 'US',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extrair informações básicas com tratamento de dados
                def safe_get(data, key, default='N/A'):
                    value = data.get(key, default)
                    if value is None or value == '' or value == 'None':
                        return default
                    return value
                
                def format_duration(seconds):
                    if not seconds or seconds == 0:
                        return 'N/A'
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    secs = seconds % 60
                    if hours > 0:
                        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
                    return f"{minutes:02d}:{secs:02d}"
                
                def format_views(view_count):
                    if not view_count or view_count == 0:
                        return 'N/A'
                    if view_count >= 1000000:
                        return f"{view_count/1000000:.1f}M"
                    elif view_count >= 1000:
                        return f"{view_count/1000:.1f}K"
                    return str(view_count)
                
                video_info = {
                    'title': safe_get(info, 'title', 'Título não disponível'),
                    'duration': format_duration(safe_get(info, 'duration', 0)),
                    'thumbnail': safe_get(info, 'thumbnail', ''),
                    'uploader': safe_get(info, 'uploader', 'Canal desconhecido'),
                    'view_count': format_views(safe_get(info, 'view_count', 0)),
                    'upload_date': safe_get(info, 'upload_date', 'Data não disponível'),
                    'description': safe_get(info, 'description', 'Descrição não disponível')[:500] + ('...' if len(safe_get(info, 'description', '')) > 500 else '')
                }
                
                return jsonify({
                    'success': True,
                    'video_info': video_info
                })
                
        except Exception as e:
            # Método alternativo usando configurações mais simples
            try:
                simple_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,
                    'user_agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                }
                
                with yt_dlp.YoutubeDL(simple_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Usar as mesmas funções de formatação
                    def safe_get(data, key, default='N/A'):
                        value = data.get(key, default)
                        if value is None or value == '' or value == 'None':
                            return default
                        return value
                    
                    def format_duration(seconds):
                        if not seconds or seconds == 0:
                            return 'N/A'
                        hours = seconds // 3600
                        minutes = (seconds % 3600) // 60
                        secs = seconds % 60
                        if hours > 0:
                            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
                        return f"{minutes:02d}:{secs:02d}"
                    
                    def format_views(view_count):
                        if not view_count or view_count == 0:
                            return 'N/A'
                        if view_count >= 1000000:
                            return f"{view_count/1000000:.1f}M"
                        elif view_count >= 1000:
                            return f"{view_count/1000:.1f}K"
                        return str(view_count)
                    
                    video_info = {
                        'title': safe_get(info, 'title', 'Título não disponível'),
                        'duration': format_duration(safe_get(info, 'duration', 0)),
                        'thumbnail': safe_get(info, 'thumbnail', ''),
                        'uploader': safe_get(info, 'uploader', 'Canal desconhecido'),
                        'view_count': format_views(safe_get(info, 'view_count', 0)),
                        'upload_date': safe_get(info, 'upload_date', 'Data não disponível'),
                        'description': 'Informações limitadas devido a restrições do YouTube'
                    }
                    
                    return jsonify({
                        'success': True,
                        'video_info': video_info,
                        'warning': 'Informações obtidas com método alternativo'
                    })
                    
            except Exception as e2:
                # Último recurso: usar web scraping para extrair dados reais
                video_id_match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    
                    # Tentar web scraping para obter dados reais
                    scraped_data = extract_video_data_from_html(video_id)
                    
                    if scraped_data:
                        # Usar dados extraídos do web scraping
                        def format_duration(seconds):
                            if not seconds or seconds == 0:
                                return 'N/A'
                            hours = seconds // 3600
                            minutes = (seconds % 3600) // 60
                            secs = seconds % 60
                            if hours > 0:
                                return f"{hours:02d}:{minutes:02d}:{secs:02d}"
                            return f"{minutes:02d}:{secs:02d}"
                        
                        def format_views(view_count):
                            if not view_count or view_count == 0:
                                return 'N/A'
                            if view_count >= 1000000:
                                return f"{view_count/1000000:.1f}M"
                            elif view_count >= 1000:
                                return f"{view_count/1000:.1f}K"
                            return str(view_count)
                        
                        video_info = {
                            'title': scraped_data['title'],
                            'duration': format_duration(scraped_data['duration']),
                            'thumbnail': scraped_data['thumbnail'],
                            'uploader': scraped_data['uploader'],
                            'view_count': format_views(scraped_data['view_count']),
                            'upload_date': scraped_data['upload_date'],
                            'description': scraped_data['description']
                        }
                        
                        return jsonify({
                            'success': True,
                            'video_info': video_info,
                            'video_id': video_id,
                            'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
                            'method': 'web_scraping'
                        })
                    else:
                        # Fallback final: informações básicas
                        return jsonify({
                            'success': True,
                            'video_info': {
                                'title': f'Vídeo YouTube (ID: {video_id})',
                                'duration': 'N/A',
                                'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                                'uploader': 'Canal não identificado',
                                'view_count': 'N/A',
                                'upload_date': 'Data não disponível',
                                'description': 'Informações não disponíveis devido a restrições do YouTube. Use o link direto para acessar o vídeo.'
                            },
                            'warning': 'Informações limitadas - YouTube bloqueou acesso detalhado',
                            'video_id': video_id,
                            'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
                            'direct_link': f'https://www.youtube.com/watch?v={video_id}'
                        })
                else:
                    return jsonify({'error': f'Erro ao obter informações do vídeo: {str(e)}'}), 500
    
    @app.route('/api/formats', methods=['POST'])
    def get_formats():
        """Obter formatos disponíveis para download"""
        if not request.is_json:
            return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL não fornecida.'}), 400
        
        if not YOUTUBE_URL_PATTERN.match(url):
            return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

        try:
            # Configurações para obter formatos
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'listformats': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                formats = []
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('vcodec') != 'none' or fmt.get('acodec') != 'none':  # Apenas formatos com vídeo ou áudio
                            formats.append({
                                'format_id': fmt.get('format_id', 'unknown'),
                                'ext': fmt.get('ext', 'unknown'),
                                'resolution': fmt.get('resolution', 'unknown'),
                                'quality': fmt.get('quality', 0),
                                'filesize': fmt.get('filesize', 0),
                                'vcodec': fmt.get('vcodec', 'none'),
                                'acodec': fmt.get('acodec', 'none'),
                                'fps': fmt.get('fps', 0)
                            })
                
                return jsonify({
                    'success': True,
                    'formats': formats[:20],  # Limitar a 20 formatos
                    'total_formats': len(formats)
                })
                
        except Exception as e:
            # Fallback: retornar formatos padrão
            default_formats = [
                {'format_id': 'best', 'ext': 'mp4', 'resolution': 'Melhor qualidade', 'quality': 10, 'vcodec': 'avc1', 'acodec': 'mp4a'},
                {'format_id': 'worst', 'ext': 'mp4', 'resolution': 'Menor qualidade', 'quality': 1, 'vcodec': 'avc1', 'acodec': 'mp4a'},
                {'format_id': 'audio', 'ext': 'mp3', 'resolution': 'Apenas áudio', 'quality': 5, 'vcodec': 'none', 'acodec': 'mp3'}
            ]
            
            return jsonify({
                'success': True,
                'formats': default_formats,
                'warning': 'Formatos limitados devido a restrições do YouTube',
                'error': str(e)
            })

    @app.route('/api/download', methods=['POST'])
    def download_video():
        """Download de vídeo com redirecionamento para URL direta"""
        if not request.is_json:
            return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

        data = request.get_json()
        url = data.get('url')
        quality = data.get('quality', 'best')
        format_type = data.get('format', 'mp4')

        if not url:
            return jsonify({'error': 'URL não fornecida.'}), 400
        
        if not YOUTUBE_URL_PATTERN.match(url):
            return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

        try:
            # Configurações para obter URL de download direto
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': f'{quality}[ext={format_type}]' if quality != 'best' else f'best[ext={format_type}]',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'extract_flat': False,
                'no_check_certificate': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                    }
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'url' in info:
                    # Retornar URL direta para download
                    return jsonify({
                        'success': True,
                        'download_url': info['url'],
                        'title': info.get('title', 'Vídeo YouTube'),
                        'format': info.get('ext', format_type),
                        'filesize': info.get('filesize', 0),
                        'duration': info.get('duration', 0)
                    })
                else:
                    # Se não conseguir URL direta, retornar informações para download manual
                    video_id_match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', url)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        return jsonify({
                            'success': True,
                            'message': 'Download direto não disponível devido a restrições do YouTube',
                            'video_id': video_id,
                            'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
                            'alternative_download': f'https://www.youtube.com/watch?v={video_id}',
                            'suggestion': 'Use ferramentas como yt-dlp localmente ou extensões do navegador'
                        })
                    else:
                        return jsonify({'error': 'Não foi possível obter informações de download'}), 500
                        
        except Exception as e:
            # Fallback: retornar URL do YouTube para download manual
            video_id_match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', url)
            if video_id_match:
                video_id = video_id_match.group(1)
                return jsonify({
                    'success': True,
                    'message': 'Download bloqueado pelo YouTube - use link direto',
                    'video_id': video_id,
                    'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
                    'error': str(e)
                })
            else:
                return jsonify({'error': f'Erro ao processar download: {str(e)}'}), 500

    @app.route('/api/scrape', methods=['POST'])
    def scrape_video():
        """Endpoint específico para testar web scraping"""
        if not request.is_json:
            return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL não fornecida.'}), 400
        
        if not YOUTUBE_URL_PATTERN.match(url):
            return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

        video_id_match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', url)
        if video_id_match:
            video_id = video_id_match.group(1)
            scraped_data = extract_video_data_from_html(video_id)
            
            if scraped_data:
                return jsonify({
                    'success': True,
                    'method': 'web_scraping',
                    'video_id': video_id,
                    'data': scraped_data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Falha ao extrair dados via web scraping',
                    'video_id': video_id
                })
        else:
            return jsonify({'error': 'ID do vídeo não encontrado na URL'}), 400

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
                'formats': '/api/formats (POST) - Obter formatos disponíveis',
                'download': '/api/download (POST) - Download de vídeo',
                'scrape': '/api/scrape (POST) - Testar web scraping',
                'test': '/api/test (GET) - Testar API'
            },
            'usage': {
                'info': {
                    'method': 'POST',
                    'body': {'url': 'https://www.youtube.com/watch?v=VIDEO_ID'},
                    'description': 'Obtém informações básicas do vídeo (yt-dlp + web scraping)'
                },
                'scrape': {
                    'method': 'POST',
                    'body': {'url': 'https://www.youtube.com/watch?v=VIDEO_ID'},
                    'description': 'Testa apenas web scraping para extrair dados'
                },
                'download': {
                    'method': 'POST',
                    'body': {'url': 'https://www.youtube.com/watch?v=VIDEO_ID', 'quality': 'best', 'format': 'mp4'},
                    'description': 'Obtém URL de download direto ou link alternativo'
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
