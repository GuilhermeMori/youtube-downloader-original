# src/utils/serverless_extractor.py

import yt_dlp
import random
import time
import json
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs
import re

class ServerlessYouTubeExtractor:
    """Extrator do YouTube otimizado para ambientes serverless (Vercel, etc.)"""
    
    def __init__(self):
        self.user_agents = [
            # Navegadores modernos mais comuns
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            # Mobile
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        ]
        
        self.referers = [
            'https://www.youtube.com/',
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            'https://www.youtube.com/results?search_query=',
        ]
        
        self.retry_count = 5
        self.base_delay = 1
        self.max_delay = 10
        
    def get_random_headers(self) -> Dict[str, str]:
        """Gera headers aleatórios para simular diferentes navegadores"""
        user_agent = random.choice(self.user_agents)
        referer = random.choice(self.referers)
        
        # Detecta se é mobile baseado no User-Agent
        is_mobile = any(mobile in user_agent.lower() for mobile in ['mobile', 'iphone', 'android'])
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': random.choice([
                'en-US,en;q=0.9',
                'pt-BR,pt;q=0.9,en;q=0.8',
                'es-ES,es;q=0.9,en;q=0.8',
                'fr-FR,fr;q=0.9,en;q=0.8',
                'de-DE,de;q=0.9,en;q=0.8'
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
    
    def get_ydl_opts(self, use_alternative_client: bool = False) -> Dict[str, Any]:
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
    
    def extract_video_id(self, url: str) -> Optional[str]:
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
    
    def get_video_info_with_fallback(self, url: str) -> Dict[str, Any]:
        """Obtém informações do vídeo com múltiplas estratégias de fallback"""
        video_id = self.extract_video_id(url)
        if not video_id:
            raise Exception('URL do YouTube inválida')
        
        # Estratégia 1: Tentar com cliente web padrão
        for attempt in range(self.retry_count):
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
                    
                    if attempt < self.retry_count - 1:
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
                        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                        time.sleep(delay + random.uniform(0, 1))
                        continue
                
                # Se é a última tentativa, relança o erro
                if attempt == self.retry_count - 1:
                    # Retorna informações básicas como fallback final
                    return self._get_minimal_info(video_id, url)
                
                # Espera antes da próxima tentativa
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                time.sleep(delay + random.uniform(0, 1))
        
        # Fallback final
        return self._get_minimal_info(video_id, url)
    
    def _format_video_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def _get_fallback_info(self, video_id: str) -> Optional[Dict[str, Any]]:
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
    
    def _get_minimal_info(self, video_id: str, url: str) -> Dict[str, Any]:
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
    
    def _extract_formats(self, formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    def _format_duration(self, duration: int) -> str:
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
    
    def _format_number(self, number: int) -> str:
        """Formata números grandes de forma legível"""
        if not number:
            return 'N/A'
        
        if number >= 1_000_000:
            return f"{number/1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number/1_000:.1f}K"
        else:
            return str(number)
    
    def _format_date(self, date_str: str) -> str:
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
