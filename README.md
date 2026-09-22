# Inventário TI

Aplicação web para controle de aparelhos, chips, estoque, devoluções, descarte e manutenções. Desenvolvida com Flask e compatível com SQLite e PostgreSQL.

## Tecnologias

- Python 3.12+
- Flask
- SQLite para uso local ou PostgreSQL em produção
- Docker Compose (opcional)

## Configuração local

```powershell
git clone <URL-DO-SEU-REPOSITORIO>
cd inventario-ti
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

A aplicação estará disponível em `http://127.0.0.1:5000`.

Por padrão, o sistema usa o banco SQLite local. Para usar PostgreSQL, configure `DATABASE_URL` no arquivo `.env`:

```text
DATABASE_URL=postgresql://usuario:senha@host:5432/inventario_ti
```

## Variáveis de ambiente

| Variável | Uso |
| --- | --- |
| `SECRET_KEY` | Chave de sessão do Flask; obrigatória em produção. |
| `FLASK_DEBUG` | Use `1` apenas no desenvolvimento local. |
| `DATABASE_URL` | Conexão PostgreSQL; vazia para usar SQLite. |
| `PULSUS_TOKEN` | Token da integração Pulsus, caso utilizada. |
| `OPENEDGE_URL`, `OPENEDGE_USER`, `OPENEDGE_PASSWORD` | Dados da integração OpenEdge, caso utilizada. |
| `OPENEDGE_JAR` | Caminho para o driver JDBC OpenEdge. |

## Estrutura

```text
app.py                 Inicialização da aplicação
database.py            Conexões e consultas ao banco
models.py              Esquema e definições SQL
routes/                Módulos e rotas Flask
templates/             Templates HTML
static/                CSS, JavaScript e imagens
migrations/            Evolução versionada do banco
importar_planilha.py   Importação de dados por planilha
```

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

O serviço ficará disponível em `http://localhost:5000`.

> A integração OpenEdge usa o arquivo `openedge.jar` na raiz do projeto. Antes de publicar o repositório, confirme que a licença do driver permite redistribuição.

## Versionamento

O Git ignora credenciais, bancos locais, ambientes virtuais e planilhas temporárias. Mantenha o arquivo `.env` apenas no ambiente onde a aplicação será executada.

## Screenshots

> Adicione as imagens em `docs/images/` e substitua os caminhos abaixo quando elas estiverem disponíveis.

### Dashboard

![Dashboard](docs/images/dashboard.png)

### Inventário de aparelhos

![Inventário](docs/images/inventario.png)

### Gestão de chips

![Chips](docs/images/chips.png)

### Estoque

![Estoque](docs/images/estoque.png)
