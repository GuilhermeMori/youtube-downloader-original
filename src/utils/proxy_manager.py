# src/utils/proxy_manager.py

import random
import requests
import time
from typing import List, Optional

class ProxyManager:
    """Gerenciador de proxies para contornar bloqueios do YouTube"""
    
    def __init__(self):
        self.proxies = []
        self.current_proxy_index = 0
        self.failed_proxies = set()
        
    def load_free_proxies(self) -> List[str]:
        """Carrega uma lista de proxies gratuitos"""
        # Lista de proxies públicos gratuitos (atualizar conforme necessário)
        free_proxies = [
            # Proxies HTTP/HTTPS gratuitos
            "http://103.149.162.194:80",
            "http://103.149.162.195:80", 
            "http://103.149.162.196:80",
            "http://103.149.162.197:80",
            "http://103.149.162.198:80",
            # Adicione mais proxies conforme necessário
        ]
        return free_proxies
    
    def test_proxy(self, proxy: str, timeout: int = 10) -> bool:
        """Testa se um proxy está funcionando"""
        try:
            response = requests.get(
                'https://httpbin.org/ip',
                proxies={'http': proxy, 'https': proxy},
                timeout=timeout
            )
            return response.status_code == 200
        except:
            return False
    
    def get_working_proxy(self) -> Optional[str]:
        """Retorna um proxy que está funcionando"""
        if not self.proxies:
            self.proxies = self.load_free_proxies()
        
        # Remove proxies que falharam
        self.proxies = [p for p in self.proxies if p not in self.failed_proxies]
        
        if not self.proxies:
            return None
        
        # Testa proxies em ordem aleatória
        random.shuffle(self.proxies)
        
        for proxy in self.proxies:
            if self.test_proxy(proxy):
                return proxy
            else:
                self.failed_proxies.add(proxy)
        
        return None
    
    def get_proxy_dict(self, proxy: str) -> dict:
        """Converte string do proxy para dicionário usado pelo yt-dlp"""
        return {
            'http': proxy,
            'https': proxy
        }

class UserAgentRotator:
    """Rotaciona User-Agents para evitar detecção"""
    
    def __init__(self):
        self.user_agents = [
            # Chrome no Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            
            # Firefox no Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
            
            # Chrome no macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            
            # Safari no macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            
            # Chrome no Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]
    
    def get_random_user_agent(self) -> str:
        """Retorna um User-Agent aleatório"""
        return random.choice(self.user_agents)

class RequestThrottler:
    """Controla a velocidade das requisições para evitar rate limiting"""
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0
    
    def wait_if_needed(self):
        """Espera o tempo necessário antes da próxima requisição"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        delay = random.uniform(self.min_delay, self.max_delay)
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

