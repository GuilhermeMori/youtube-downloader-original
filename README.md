# YouTube Downloader

Uma aplicação web Flask para download de vídeos do YouTube com interface moderna e API RESTful.

## Funcionalidades

- ✅ Download de vídeos do YouTube em diferentes qualidades
- ✅ Suporte a múltiplos formatos (MP4, WebM, MP3)
- ✅ Interface web responsiva
- ✅ API RESTful para integração
- ✅ Validação de URLs do YouTube
- ✅ Informações detalhadas dos vídeos
- ✅ Sistema de usuários com banco de dados SQLite

## Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Download**: yt-dlp
- **Banco de Dados**: SQLite com SQLAlchemy
- **Frontend**: HTML/CSS/JavaScript
- **CORS**: Flask-CORS para requisições cross-origin

## Instalação

### Pré-requisitos

- Python 3.8+
- pip

### Passos para instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd youtube-downloader
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute a aplicação:
```bash
python main.py
```

A aplicação estará disponível em `http://localhost:5000`

## Estrutura do Projeto

```
youtube-downloader/
├── main.py                 # Arquivo principal da aplicação
├── requirements.txt        # Dependências Python
├── .gitignore             # Arquivos ignorados pelo Git
├── database/              # Banco de dados SQLite
│   └── app.db
├── src/                   # Código fonte
│   ├── __init__.py
│   ├── models/            # Modelos do banco de dados
│   └── routes/            # Rotas da API
│       ├── user.py        # Rotas de usuário
│       └── youtube.py     # Rotas do YouTube
└── static/                # Arquivos estáticos
    └── index.html         # Interface web
```

## API Endpoints

### YouTube

- `POST /api/info` - Obter informações do vídeo
- `POST /api/download` - Download do vídeo
- `GET /api/formats` - Listar formatos disponíveis

### Usuários

- `POST /api/register` - Registrar usuário
- `POST /api/login` - Login de usuário

## Uso

### Interface Web

Acesse `http://localhost:5000` e cole a URL do YouTube no campo de entrada.

### API

```bash
# Obter informações do vídeo
curl -X POST http://localhost:5000/api/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'

# Download do vídeo
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "quality": "720p", "format": "mp4"}'
```

## Formatos Suportados

- **Vídeo**: MP4, WebM, MKV
- **Áudio**: MP3, M4A, WebM (audio only)
- **Qualidades**: 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p

## Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## Aviso Legal

Este projeto é apenas para fins educacionais. Respeite os termos de serviço do YouTube e as leis de direitos autorais aplicáveis em sua jurisdição.
