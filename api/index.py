# api/index.py - Vercel serverless function ultra-simplificada

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
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
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
    
    def get_video_info_from_html(video_id):
        """Extrai informações do vídeo via web scraping"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = get_random_headers()
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
                
            html = response.text
            
            # Extrair título
            title = f'Vídeo YouTube (ID: {video_id})'
            title_match = re.search(r'<title>([^<]+)</title>', html)
            if title_match:
                title = title_match.group(1).replace(' - YouTube', '').strip()
            
            # Extrair descrição
            description = 'Descrição não disponível'
            desc_patterns = [
                r'"description":"([^"]+)"',
                r'"shortDescription":"([^"]+)"',
                r'<meta name="description" content="([^"]+)"',
            ]
            
            for pattern in desc_patterns:
                desc_match = re.search(pattern, html)
                if desc_match:
                    description = desc_match.group(1)[:200] + '...'
                    break
            
            # Extrair canal
            uploader = 'Canal não identificado'
            channel_patterns = [
                r'"ownerText":\{"runs":\[\{"text":"([^"]+)"',
                r'"channelName":"([^"]+)"',
                r'"author":"([^"]+)"',
                r'<link rel="canonical" href="https://www\.youtube\.com/channel/[^"]+">([^<]+)</link>',
            ]
            
            for pattern in channel_patterns:
                channel_match = re.search(pattern, html)
                if channel_match:
                    uploader = channel_match.group(1)
                    break
            
            # Extrair visualizações
            view_count = 'N/A'
            view_patterns = [
                r'"viewCount":"(\d+)"',
                r'"view_count":"(\d+)"',
                r'(\d+(?:,\d+)*)\s*visualizações',
                r'(\d+(?:,\d+)*)\s*views',
            ]
            
            for pattern in view_patterns:
                view_match = re.search(pattern, html)
                if view_match:
                    view_count = format_number(int(view_match.group(1).replace(',', '')))
                    break
            
            # Extrair duração
            duration = 'N/A'
            duration_patterns = [
                r'"lengthSeconds":"(\d+)"',
                r'"duration":"PT(\d+)S"',
                r'(\d+):(\d+):(\d+)',
                r'(\d+):(\d+)',
            ]
            
            for pattern in duration_patterns:
                duration_match = re.search(pattern, html)
                if duration_match:
                    if ':' in duration_match.group(0):
                        # Formato HH:MM:SS ou MM:SS
                        parts = duration_match.group(0).split(':')
                        if len(parts) == 3:
                            hours, minutes, seconds = map(int, parts)
                            duration = format_duration(hours * 3600 + minutes * 60 + seconds)
                        elif len(parts) == 2:
                            minutes, seconds = map(int, parts)
                            duration = format_duration(minutes * 60 + seconds)
                    else:
                        # Formato em segundos
                        duration = format_duration(int(duration_match.group(1)))
                    break
            
            return {
                'title': title,
                'description': description,
                'uploader': uploader,
                'view_count': view_count,
                'duration': duration,
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            }
            
        except Exception as e:
            print(f"Erro no web scraping: {e}")
            return None
    
    def get_video_info_with_fallback(url):
        """Obtém informações do vídeo com múltiplas estratégias de fallback"""
        video_id = extract_video_id(url)
        if not video_id:
            raise Exception('URL do YouTube inválida')
        
        # Estratégia 1: API não oficial do YouTube
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
        
        # Estratégia 2: Web scraping
        try:
            scraped_data = get_video_info_from_html(video_id)
            if scraped_data:
                return {
                    'success': True,
                    'video_id': video_id,
                    'title': scraped_data['title'],
                    'description': scraped_data['description'],
                    'duration': scraped_data['duration'],
                    'uploader': scraped_data['uploader'],
                    'view_count': scraped_data['view_count'],
                    'upload_date': 'Data não disponível',
                    'thumbnail': scraped_data['thumbnail'],
                    'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
                    'direct_link': f'https://www.youtube.com/watch?v={video_id}',
                    'formats': []
                }
        except Exception as e:
            print(f"Erro no web scraping: {e}")
        
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
        # Se for uma rota da API, retorna JSON
        if path.startswith('api/'):
            return jsonify({
                'message': 'YouTube Downloader API is running!',
                'version': '2.1.0',
                'status': 'online',
                'endpoints': ['/api/info', '/api/download', '/api/health', '/api/test']
            })
        
        # Para outras rotas, serve o arquivo estático
        static_folder = os.path.join(parent_dir, 'static')
        
        # Se o arquivo existe na pasta static, serve ele
        if path and os.path.exists(os.path.join(static_folder, path)):
            return send_from_directory(static_folder, path)
        
        # Senão, serve o index.html
        index_path = os.path.join(static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder, 'index.html')
        
        # Fallback: retorna a aplicação básica
        return """
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>YouTube Downloader</title>
            <style>
                body { font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
                .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); width: 100%; max-width: 500px; text-align: center; }
                h1 { color: #333; }
                input[type="text"] { width: calc(100% - 22px); padding: 10px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 4px; }
                button { background-color: #ff0000; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; transition: background-color 0.3s; margin: 5px; }
                #info-btn { background-color: #007bff; }
                button:disabled { background-color: #f88; cursor: not-allowed; }
                button:hover:not(:disabled) { background-color: #cc0000; }
                #video-info { margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 4px; text-align: left; display: none; }
                #video-info h3 { margin-top: 0; color: #333; }
                #format-selection { margin: 20px 0; padding: 15px; background-color: #f0f8ff; border-radius: 4px; text-align: left; }
                #format-selection label { display: block; margin-bottom: 10px; font-weight: bold; color: #333; }
                #format-select { width: 100%; padding: 8px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
                #status { margin-top: 20px; font-size: 1em; color: #555; }
                .success { color: green; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>YouTube Downloader</h1>
                <p>Cole a URL do vídeo do YouTube para baixar na melhor qualidade disponível.</p>
                <input type="text" id="youtube-url" placeholder="https://www.youtube.com/watch?v=...">
                <button id="info-btn">Obter Informações</button>
                <div id="video-info"></div>
                <div id="format-selection" style="display: none;">
                    <label for="format-select">Escolha a resolução:</label>
                    <select id="format-select">
                        <option value="">Selecione uma resolução...</option>
                    </select>
                    <button id="download-btn">Baixar Vídeo</button>
                </div>
                <div id="status"></div>
            </div>

            <script>
                const urlInput = document.getElementById('youtube-url');
                const infoBtn = document.getElementById('info-btn');
                const downloadBtn = document.getElementById('download-btn');
                const videoInfoDiv = document.getElementById('video-info');
                const formatSelectionDiv = document.getElementById('format-selection');
                const formatSelect = document.getElementById('format-select');
                const statusDiv = document.getElementById('status');

                infoBtn.addEventListener('click', async () => {
                    const url = urlInput.value.trim();
                    if (!url) {
                        showStatus('Por favor, insira uma URL do YouTube.', 'error');
                        return;
                    }

                    infoBtn.disabled = true;
                    infoBtn.textContent = 'Carregando...';
                    showStatus('Obtendo informações do vídeo...', '');

                    try {
                        const response = await fetch('/api/info', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ url: url }),
                        });

                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.error || `Erro ${response.status}: ${response.statusText}`);
                        }

                        const info = await response.json();
                        showVideoInfo(info);
                        showFormatOptions(info.formats);
                        showStatus('Informações carregadas com sucesso! Escolha a resolução desejada.', 'success');

                    } catch (error) {
                        showStatus(error.message, 'error');
                        videoInfoDiv.style.display = 'none';
                        formatSelectionDiv.style.display = 'none';
                    } finally {
                        infoBtn.disabled = false;
                        infoBtn.textContent = 'Obter Informações';
                    }
                });

                downloadBtn.addEventListener('click', async () => {
                    const url = urlInput.value.trim();
                    const selectedFormat = formatSelect.value;

                    if (!url) {
                        showStatus('Por favor, insira uma URL do YouTube.', 'error');
                        return;
                    }

                    if (!selectedFormat) {
                        showStatus('Por favor, escolha uma resolução antes de baixar.', 'error');
                        return;
                    }

                    downloadBtn.disabled = true;
                    downloadBtn.textContent = 'Baixando...';
                    showStatus('Iniciando download, por favor aguarde...', '');

                    try {
                        const response = await fetch('/api/download', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ url: url, format_id: selectedFormat }),
                        });

                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.error || `Erro ${response.status}: ${response.statusText}`);
                        }

                        const data = await response.json();
                        showStatus(`Download iniciado! Link: ${data.direct_link}`, 'success');

                    } catch (error) {
                        showStatus(error.message, 'error');
                    } finally {
                        downloadBtn.disabled = false;
                        downloadBtn.textContent = 'Baixar Vídeo';
                    }
                });

                function showStatus(message, type) {
                    statusDiv.textContent = message;
                    statusDiv.className = type;
                }

                function showVideoInfo(info) {
                    videoInfoDiv.innerHTML = `
                        <h3>${info.title}</h3>
                        <p><strong>Canal:</strong> ${info.uploader}</p>
                        <p><strong>Duração:</strong> ${info.duration}</p>
                        <p><strong>Visualizações:</strong> ${info.view_count}</p>
                        <p><strong>Descrição:</strong> ${info.description}</p>
                    `;
                    videoInfoDiv.style.display = 'block';
                }

                function showFormatOptions(formats) {
                    formatSelect.innerHTML = '<option value="">Selecione uma resolução...</option>';

                    if (formats && formats.length > 0) {
                        formats.forEach(format => {
                            const option = document.createElement('option');
                            option.value = format.format_id;
                            option.textContent = `${format.resolution} (${format.ext.toUpperCase()})`;
                            formatSelect.appendChild(option);
                        });
                        formatSelectionDiv.style.display = 'block';
                    } else {
                        formatSelectionDiv.style.display = 'none';
                        showStatus('Nenhum formato de vídeo disponível.', 'error');
                    }
                }
            </script>
        </body>
        </html>
        """

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