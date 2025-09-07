# src/utils/youtube_extractor.py

import yt_dlp
import random
import time
from typing import Dict, Any, Optional
from .proxy_manager import ProxyManager, UserAgentRotator, RequestThrottler

class AntiDetectionYouTubeExtractor:
    """Extrator do YouTube com recursos anti-detecção"""
    
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.user_agent_rotator = UserAgentRotator()
        self.throttler = RequestThrottler()
        self.retry_count = 3
        
    def get_base_ydl_opts(self) -> Dict[str, Any]:
        """Retorna configurações base do yt-dlp com anti-detecção"""
        user_agent = self.user_agent_rotator.get_random_user_agent()
        
        opts = {
            # Configurações básicas
            'quiet': True,
            'no_warnings': True,
            'extractflat': False,
            'ignoreerrors': False,
            
            # Anti-detecção
            'user_agent': user_agent,
            'referer': 'https://www.youtube.com/',
            
            # Headers customizados para simular navegador real
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            },
            
            # Configurações de rede
            'socket_timeout': 30,
            'retries': self.retry_count,
            'fragment_retries': self.retry_count,
            
            # Simula comportamento de navegador
            'sleep_interval': random.uniform(1, 3),
            'max_sleep_interval': 5,
            
            # Configurações de cookies (simula sessão de navegador)
            'cookiefile': None,  # Pode ser configurado para usar cookies salvos
            
            # Evita detecção de bot
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],  # Evita alguns formatos que podem ser detectados
                    'player_client': ['android', 'web'],  # Usa clientes alternativos
                }
            }
        }
        
        return opts
    
    def add_proxy_to_opts(self, opts: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona configuração de proxy às opções do yt-dlp"""
        proxy = self.proxy_manager.get_working_proxy()
        if proxy:
            opts['proxy'] = proxy
            print(f"Usando proxy: {proxy}")
        return opts
    
    def extract_info_with_retry(self, url: str, download: bool = False, use_proxy: bool = True) -> Optional[Dict[str, Any]]:
        """Extrai informações com retry e anti-detecção"""
        
        for attempt in range(self.retry_count):
            try:
                # Espera antes da requisição para evitar rate limiting
                self.throttler.wait_if_needed()
                
                # Configura opções base
                opts = self.get_base_ydl_opts()
                
                # Adiciona proxy se solicitado
                if use_proxy and attempt > 0:  # Usa proxy após primeira tentativa falhar
                    opts = self.add_proxy_to_opts(opts)
                
                # Rotaciona User-Agent a cada tentativa
                if attempt > 0:
                    opts['user_agent'] = self.user_agent_rotator.get_random_user_agent()
                    opts['http_headers']['User-Agent'] = opts['user_agent']
                
                # Executa extração
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info_dict = ydl.extract_info(url, download=download)
                    return info_dict
                    
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e).lower()
                
                # Verifica se é erro de bloqueio
                if any(keyword in error_msg for keyword in ['blocked', 'forbidden', '403', 'rate limit', 'too many requests']):
                    print(f"Tentativa {attempt + 1}: Detectado bloqueio, tentando com proxy...")
                    if attempt < self.retry_count - 1:
                        # Espera mais tempo antes da próxima tentativa
                        time.sleep(random.uniform(5, 10))
                        continue
                
                # Outros erros específicos
                if 'private video' in error_msg:
                    raise Exception('Este vídeo é privado e não pode ser acessado.')
                if 'video unavailable' in error_msg:
                    raise Exception('Este vídeo não está disponível.')
                
                # Se é a última tentativa, relança o erro
                if attempt == self.retry_count - 1:
                    raise Exception(f'Não foi possível acessar o vídeo após {self.retry_count} tentativas.')
                
                # Espera antes da próxima tentativa
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                if attempt == self.retry_count - 1:
                    raise Exception(f'Erro inesperado: {str(e)}')
                
                # Espera antes da próxima tentativa
                time.sleep(random.uniform(2, 5))
        
        return None
    
    def get_download_opts(self, format_id: Optional[str] = None, output_dir: str = '/tmp') -> Dict[str, Any]:
        """Retorna configurações otimizadas para download"""
        opts = self.get_base_ydl_opts()
        
        # Configurações específicas para download
        opts.update({
            'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
            'noplaylist': True,
            
            # Otimizações de velocidade
            'concurrent_fragment_downloads': 4,
            'http_chunk_size': 10485760,  # 10MB chunks
            
            # Preserva metadados
            'writeinfojson': True,
            'writethumbnail': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            
            # Configurações de merge
            'merge_output_format': 'mp4',
            'keepvideo': False,
            
            # Post-processadores
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        })
        
        # Configuração de formato
        if format_id:
            # Verifica se o formato tem áudio
            opts['format'] = f'{format_id}+bestaudio[ext=m4a]/bestaudio'
        else:
            opts['format'] = 'best[height>=720][ext=mp4]/best[height>=480][ext=mp4]/best'
        
        return opts
    
    def download_with_anti_detection(self, url: str, format_id: Optional[str] = None, output_dir: str = '/tmp') -> str:
        """Baixa vídeo com anti-detecção"""
        
        for attempt in range(self.retry_count):
            try:
                # Espera antes da requisição
                self.throttler.wait_if_needed()
                
                # Configura opções de download
                opts = self.get_download_opts(format_id, output_dir)
                
                # Adiciona proxy se necessário
                if attempt > 0:
                    opts = self.add_proxy_to_opts(opts)
                
                # Rotaciona User-Agent
                if attempt > 0:
                    opts['user_agent'] = self.user_agent_rotator.get_random_user_agent()
                    opts['http_headers']['User-Agent'] = opts['user_agent']
                
                # Executa download
                with yt_dlp.YoutubeDL(opts) as ydl:
                    # Primeiro extrai info para obter nome do arquivo
                    info_dict = ydl.extract_info(url, download=False)
                    filename = ydl.prepare_filename(info_dict)
                    
                    # Depois faz o download
                    ydl.download([url])
                    
                    return filename
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                if any(keyword in error_msg for keyword in ['blocked', 'forbidden', '403', 'rate limit']):
                    print(f"Download tentativa {attempt + 1}: Detectado bloqueio, tentando com proxy...")
                    if attempt < self.retry_count - 1:
                        time.sleep(random.uniform(5, 10))
                        continue
                
                if attempt == self.retry_count - 1:
                    raise Exception(f'Não foi possível baixar o vídeo após {self.retry_count} tentativas: {str(e)}')
                
                time.sleep(random.uniform(2, 5))
        
        raise Exception('Falha no download após todas as tentativas')

