# Guia de Deploy - YouTube Downloader com Anti-Detecção

## Passo a Passo para Deploy na Vercel

### 1. Preparação dos Arquivos

Substitua os arquivos originais pelos melhorados:

```bash
# Backup dos arquivos originais (opcional)
cp main.py main_original.py
cp requirements.txt requirements_original.txt
cp vercel.json vercel_original.json

# Substitua pelos arquivos melhorados
cp main_improved.py main.py
cp requirements_improved.txt requirements.txt
cp vercel_improved.json vercel.json
```

### 2. Estrutura Final do Projeto

Certifique-se de que seu projeto tenha esta estrutura:

```
youtube-downloader/
├── main.py (versão melhorada)
├── requirements.txt (versão melhorada)
├── vercel.json (versão melhorada)
├── src/
│   ├── utils/
│   │   ├── proxy_manager.py (NOVO)
│   │   └── youtube_extractor.py (NOVO)
│   └── routes/
│       ├── youtube.py (original)
│       └── youtube_improved.py (NOVO)
├── static/ (seus arquivos frontend)
└── database/ (será criado automaticamente)
```

### 3. Deploy na Vercel

#### Opção A: Via CLI da Vercel

```bash
# Instale a CLI da Vercel
npm i -g vercel

# Faça login
vercel login

# Deploy
vercel --prod
```

#### Opção B: Via GitHub

1. Faça push das alterações para seu repositório GitHub
2. Conecte o repositório na dashboard da Vercel
3. A Vercel detectará automaticamente o `vercel.json` melhorado

### 4. Configurações Importantes na Vercel

Na dashboard da Vercel, configure:

#### Environment Variables (se necessário):
- `FLASK_ENV=production`
- `PYTHONPATH=.`

#### Function Settings:
- **Timeout**: 300 segundos (máximo)
- **Memory**: 1024MB (recomendado)
- **Runtime**: Python 3.9

### 5. Testando o Deploy

Após o deploy, teste os novos endpoints:

#### Teste de Status
```bash
curl https://seu-app.vercel.app/api/status
```

#### Teste de Health Check
```bash
curl https://seu-app.vercel.app/api/health-check
```

#### Teste de Informações (Anti-Detecção)
```bash
curl -X POST https://seu-app.vercel.app/api/info-improved \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### 6. Monitoramento

#### Logs da Vercel
```bash
vercel logs seu-app.vercel.app
```

#### Endpoint de Monitoramento
Configure um monitor para verificar regularmente:
```bash
curl https://seu-app.vercel.app/api/health-check
```

### 7. Troubleshooting

#### Erro de Timeout
- Aumente o timeout na configuração da função
- Use formatos de vídeo menores para testes

#### Erro de Memória
- Aumente a memória alocada para 1024MB
- Otimize o processamento de vídeos grandes

#### Bloqueios Persistentes
- Verifique os logs para identificar padrões
- Considere implementar proxies pagos
- Ajuste os delays entre requisições

### 8. Próximos Passos

#### Implementar Proxies Pagos
Edite `src/utils/proxy_manager.py` para adicionar seus proxies:

```python
def load_free_proxies(self) -> List[str]:
    return [
        "http://seu-proxy-premium-1:8080",
        "http://seu-proxy-premium-2:8080",
        # Adicione mais proxies pagos
    ]
```

#### Configurar Domínios Múltiplos
- Deploy em múltiplos provedores (Vercel, Netlify, Railway)
- Implemente load balancing entre domínios

#### Monitoramento Avançado
- Configure alertas para quando endpoints falharem
- Implemente métricas de sucesso/falha
- Configure logs estruturados

### 9. Manutenção

#### Atualizações Regulares
```bash
# Atualize o yt-dlp regularmente
pip install --upgrade yt-dlp

# Teste localmente antes do deploy
python main.py

# Deploy das atualizações
vercel --prod
```

#### Backup de Configurações
- Mantenha backup dos arquivos de configuração
- Documente mudanças nas estratégias anti-detecção
- Monitore efetividade das soluções

### 10. Considerações Legais

- ⚠️ **Importante**: Use apenas para conteúdo que você tem direito de baixar
- Respeite os termos de serviço do YouTube
- Considere implementar rate limiting adicional
- Monitore o uso para evitar abuso

### 11. Suporte

Se encontrar problemas:

1. Verifique os logs da Vercel
2. Teste localmente primeiro
3. Consulte a documentação do yt-dlp
4. Considere ajustar as configurações de anti-detecção

### 12. Alternativas de Deploy

#### Railway
```bash
# Instale a CLI do Railway
npm install -g @railway/cli

# Login e deploy
railway login
railway deploy
```

#### Render
- Conecte seu repositório GitHub
- Configure como Web Service
- Use `python main.py` como comando de start

#### Heroku
```bash
# Crie um Procfile
echo "web: python main.py" > Procfile

# Deploy
git add .
git commit -m "Deploy com anti-detecção"
git push heroku main
```

