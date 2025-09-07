# src/routes/youtube.py

import os
import re
import yt_dlp
import atexit
import shutil
import mimetypes
from flask import Blueprint, request, jsonify, send_from_directory, Response

youtube_bp = Blueprint('youtube_bp', __name__)

# Diretório temporário para processar downloads
import tempfile
downloads_dir = tempfile.mkdtemp(prefix='youtube_downloader_')

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

@youtube_bp.route('/info', methods=['POST'])
def get_video_info():
    """Get video information without downloading"""
    if not request.is_json:
        return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL não fornecida.'}), 400
    
    if not YOUTUBE_URL_PATTERN.match(url):
        print(f"URL inválida recebida no /info: {url}")  # Debug log
        return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            
            # Extrai formatos de vídeo disponíveis
            formats = info_dict.get('formats', [])
            video_formats = []
            
            # Formatos prioritários com vídeo+áudio combinados
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
            
            # Primeiro, procura por formatos que já têm vídeo+áudio
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
                
                # Formatos com vídeo E áudio (preferidos)
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
                
                # Formatos apenas com vídeo (como fallback)
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
            
            # Combina os formatos: primeiro os com áudio, depois os sem áudio
            video_formats = combined_formats + video_only_formats
            
            # Remove duplicatas baseado em altura e extensão, mantendo o melhor codec
            seen = {}
            unique_formats = []
            
            for fmt in video_formats:
                key = (fmt['height'], fmt['ext'])
                if key not in seen:
                    seen[key] = fmt
                    unique_formats.append(fmt)
                else:
                    # Se já existe, mantém o que tem melhor codec (prioriza h264/avc1 > vp9 > av1)
                    existing = seen[key]
                    current_vcodec = fmt['vcodec'].lower()
                    existing_vcodec = existing['vcodec'].lower()
                    
                    # Prioridade: H.264 > VP9 > AV1
                    if ('avc1' in current_vcodec or 'h264' in current_vcodec) and not ('avc1' in existing_vcodec or 'h264' in existing_vcodec):
                        seen[key] = fmt
                        # Remove o antigo e adiciona o novo
                        unique_formats = [f for f in unique_formats if not (f['height'] == fmt['height'] and f['ext'] == fmt['ext'])]
                        unique_formats.append(fmt)
                    elif 'vp9' in current_vcodec and not ('avc1' in existing_vcodec or 'h264' in existing_vcodec or 'vp9' in existing_vcodec):
                        seen[key] = fmt
                        # Remove o antigo e adiciona o novo
                        unique_formats = [f for f in unique_formats if not (f['height'] == fmt['height'] and f['ext'] == fmt['ext'])]
                        unique_formats.append(fmt)
            
            # Ordena por altura (maior primeiro) e depois por codec (H.264 primeiro)
            def sort_key(fmt):
                height = fmt['height']
                vcodec = fmt['vcodec'].lower()
                # Prioridade de codec: H.264=0, VP9=1, AV1=2, outros=3
                codec_priority = 0 if ('avc1' in vcodec or 'h264' in vcodec) else (1 if 'vp9' in vcodec else (2 if 'av01' in vcodec else 3))
                return (-height, codec_priority)
            
            unique_formats.sort(key=sort_key)
            
            # Filtra qualidades 360p e acima, priorizando formatos com áudio
            high_quality_formats = [fmt for fmt in unique_formats if fmt['height'] >= 360]
            
            # Ordena para mostrar formatos com áudio primeiro
            high_quality_formats.sort(key=lambda x: (not x.get('has_audio', False), -x['height']))
            
            return jsonify({
                'title': info_dict.get('title', 'Título não disponível'),
                'duration': info_dict.get('duration', 0),
                'uploader': info_dict.get('uploader', 'Desconhecido'),
                'view_count': info_dict.get('view_count', 0),
                'description': info_dict.get('description', '')[:200] + '...' if info_dict.get('description') else '',
                'formats': high_quality_formats[:10]  # Limita a 10 formatos para não sobrecarregar
            }), 200

    except yt_dlp.utils.DownloadError as e:
        error_message = str(e).lower()
        if 'private video' in error_message:
            return jsonify({'error': 'Este vídeo é privado e não pode ser acessado.'}), 403
        if 'video unavailable' in error_message:
            return jsonify({'error': 'Este vídeo não está disponível.'}), 404
        return jsonify({'error': 'Não foi possível obter informações do vídeo.'}), 500
    
    except Exception as e:
        print(f"Erro inesperado ao obter info: {e}")
        return jsonify({'error': 'Erro interno do servidor.'}), 500

@youtube_bp.route('/download', methods=['POST'])
def download_video():
    # Garante que a requisição tenha o formato JSON correto
    if not request.is_json:
        return jsonify({'error': 'Requisição inválida, esperado JSON.'}), 415

    data = request.get_json()
    url = data.get('url')
    format_id = data.get('format_id')

    if not url:
        return jsonify({'error': 'URL não fornecida.'}), 400
    
    if not YOUTUBE_URL_PATTERN.match(url):
        print(f"URL inválida recebida no /download: {url}")  # Debug log
        return jsonify({'error': 'URL do YouTube inválida. Verifique o formato.'}), 400

    try:
        # Primeiro, extrai informações do vídeo para validar o formato
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
            
            # Informações do vídeo (logs removidos para limpeza)
            
            # Verifica se o formato solicitado existe
            selected_format = None
            if format_id:
                for fmt in formats:
                    if fmt.get('format_id') == format_id:
                        selected_format = fmt
                        break
                
                if not selected_format:
                    # Lista formatos disponíveis para debug
                    available_ids = [f.get('format_id') for f in formats if f.get('format_id')]
                    return jsonify({
                        'error': f'Formato {format_id} não disponível para este vídeo.',
                        'available_formats': available_ids
                    }), 400
                
                # Formato encontrado (logs removidos para limpeza)
            else:
                # Se não especificou formato, usa o melhor disponível
                format_selector = 'bv[height>=1080]/bv[height>=720]/bv'
            
            # Determina se o formato selecionado tem áudio
            has_audio = False
            if selected_format:
                has_audio = selected_format.get('acodec') and selected_format.get('acodec') != 'none'
            
            # Configuração para download otimizada
            if format_id:
                if has_audio:
                    # Formato já tem áudio, baixa diretamente
                    format_selector = format_id
                else:
                    # Formato sem áudio, baixa vídeo + melhor áudio e combina
                    format_selector = f'{format_id}+bestaudio[ext=m4a]/bestaudio'
            else:
                # Se não especificou formato, usa o melhor com áudio
                format_selector = 'best[height>=720][ext=mp4]/best[height>=480][ext=mp4]/best'
            
            download_opts = {
                'format': format_selector,
                'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': False,
                'no_warnings': False,
                'extractflat': False,
                'ignoreerrors': False,
                
                # Otimizações de velocidade
                'concurrent_fragment_downloads': 4,  # Download paralelo de fragmentos
                'retries': 3,
                'fragment_retries': 3,
                'http_chunk_size': 10485760,  # 10MB chunks para melhor velocidade
                
                # Preserva metadados
                'writeinfojson': True,  # Salva metadados
                'writethumbnail': True,  # Salva thumbnail
                'writesubtitles': False,
                'writeautomaticsub': False,
                
                # Configurações de merge para garantir compatibilidade
                'merge_output_format': 'mp4',  # Força saída em MP4
                'keepvideo': False,  # Remove arquivos temporários após merge
                
                # Post-processadores para garantir qualidade
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }] if not has_audio else [],
            }
            
            # Inicia o download com configurações específicas
            with yt_dlp.YoutubeDL(download_opts) as download_ydl:
                download_ydl.download([url])
                # Prepara o nome do arquivo final como o yt-dlp o salvaria
                final_filename = download_ydl.prepare_filename(info_dict)
            
            # Verifica se o arquivo foi criado
            if os.path.exists(final_filename):
                file_size = os.path.getsize(final_filename)
                
                # Limpa o nome do arquivo para ser seguro para download
                safe_filename = re.sub(r'[^\w\-_\.]', '_', info_dict.get('title', 'video'))
                safe_filename = safe_filename[:100]  # Limita o tamanho do nome
                file_extension = os.path.basename(final_filename).split('.')[-1]
                download_filename = f"{safe_filename}.{file_extension}"
                
                # Configurações específicas para ngrok e downloads grandes
                
                # Determina o tipo MIME correto
                mimetype = mimetypes.guess_type(final_filename)[0] or 'application/octet-stream'
                
                def generate():
                    try:
                        with open(final_filename, 'rb') as f:
                            while True:
                                chunk = f.read(8192)  # Lê em chunks de 8KB
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
                
                # Cria resposta de streaming com headers apropriados
                response = Response(
                    generate(),
                    mimetype=mimetype,
                    headers={
                        'Content-Disposition': f'attachment; filename="{download_filename}"',
                        'Content-Length': str(file_size),
                        'Content-Type': mimetype,
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    }
                )
                
                return response
            else:
                # Verifica se existem arquivos no diretório de downloads
                files_in_dir = [f for f in os.listdir(downloads_dir) if os.path.isfile(os.path.join(downloads_dir, f))]
                if files_in_dir:
                    # Pega o arquivo mais recente (provavelmente o que acabou de ser baixado)
                    latest_file = max([os.path.join(downloads_dir, f) for f in files_in_dir], key=os.path.getctime)
                    file_size = os.path.getsize(latest_file)
                    
                    # Limpa o nome do arquivo para ser seguro para download
                    safe_filename = re.sub(r'[^\w\-_\.]', '_', info_dict.get('title', 'video'))
                    safe_filename = safe_filename[:100]  # Limita o tamanho do nome
                    file_extension = os.path.basename(latest_file).split('.')[-1]
                    download_filename = f"{safe_filename}.{file_extension}"
                    
                    # Usa o mesmo método de streaming para consistência
                    
                    mimetype = mimetypes.guess_type(latest_file)[0] or 'application/octet-stream'
                    
                    def generate():
                        try:
                            with open(latest_file, 'rb') as f:
                                while True:
                                    chunk = f.read(8192)  # Lê em chunks de 8KB
                                    if not chunk:
                                        break
                                    yield chunk
                        finally:
                            # Remove o arquivo após o streaming
                            try:
                                if os.path.exists(latest_file):
                                    os.remove(latest_file)
                            except:
                                pass
                    
                    response = Response(
                        generate(),
                        mimetype=mimetype,
                        headers={
                            'Content-Disposition': f'attachment; filename="{download_filename}"',
                            'Content-Length': str(file_size),
                            'Content-Type': mimetype,
                            'Cache-Control': 'no-cache, no-store, must-revalidate',
                            'Pragma': 'no-cache',
                            'Expires': '0'
                        }
                    )
                    
                    return response
                else:
                    return jsonify({'error': 'Falha ao baixar o arquivo. Nenhum arquivo foi criado.'}), 500

    except yt_dlp.utils.DownloadError as e:
        # Trata erros específicos do yt-dlp de forma amigável
        error_message = str(e).lower()
        if 'private video' in error_message:
            return jsonify({'error': 'Este vídeo é privado e não pode ser baixado.'}), 403
        if 'video unavailable' in error_message:
            return jsonify({'error': 'Este vídeo não está disponível.'}), 404
        if 'copyright' in error_message:
            return jsonify({'error': 'Este vídeo está protegido por direitos autorais e não pode ser baixado.'}), 403
        # Erro genérico de download
        return jsonify({'error': f'Falha no download. Verifique a URL e tente novamente.'}), 500
    
    except Exception as e:
        # Captura qualquer outro erro inesperado no servidor e retorna um JSON
        # Isso impede que o Flask envie a página de erro HTML
        print(f"Erro inesperado no servidor: {e}") # Loga o erro real no console do servidor
        return jsonify({'error': 'Ocorreu um erro interno no servidor. Tente novamente mais tarde.'}), 500


