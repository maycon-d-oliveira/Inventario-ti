# Inventário TI

Sistema web para gestão de inventário de celulares, desenvolvido em Python com Flask. Funciona com SQLite em ambiente local e PostgreSQL em produção.

## Pré-requisitos

- Python 3.12 ou superior
- Java Runtime Environment (JRE), apenas para a integração opcional com OpenEdge
- Docker e Docker Compose, apenas para execução em containers

> O arquivo `openedge.jar` é o driver JDBC da integração OpenEdge. Mantenha-o na raiz do projeto para usar essa integração e para gerar a imagem Docker. Verifique internamente se a licença permite publicá-lo no GitHub antes de tornar o repositório público.

## Variáveis de Ambiente

Copie o arquivo de exemplo para `.env` e preencha somente as integrações que utilizar. O `.env` nunca deve ser enviado ao GitHub.

```bash
Copy-Item .env.example .env
```

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| SECRET_KEY | Chave secreta do Flask (obrigatório em produção) | `sua-chave-aleatoria-aqui` |
| FLASK_DEBUG | Ativar modo debug (apenas em dev) | `0` (produção) ou `1` (dev) |
| DATABASE_URL | URL do PostgreSQL | `postgresql://user:pass@host:5432/db` |

## Arquitetura

- `app.py`: cria a aplicação Flask, carrega a configuração do banco e registra as rotas.
- `database.py`: centraliza conexão, consultas e inicialização do banco.
- `models.py`: contém os scripts SQL de SQLite e PostgreSQL.
- `routes/`: separa cada módulo funcional em um blueprint.
- `templates/`: páginas HTML com comentários explicando os blocos principais.
- `static/`: estilos e pequenos comportamentos da interface.
- `importar_planilha.py`: importa a planilha Excel inicial para o banco.
- `migrations/`: scripts SQL versionados para evoluir a estrutura do banco.

## Decisões técnicas e justificativas

- Flask foi escolhido por ser simples de manter por alguém com experiência intermediária em Python.
- SQLite foi mantido como fallback local porque não exige servidor separado e facilita testes rápidos.
- PostgreSQL pode ser usado como banco principal em produção configurando a variável `DATABASE_URL`.
- O acesso ao banco usa SQL explícito em vez de ORM para deixar as consultas mais transparentes e fáceis de depurar.
- Blueprints foram usados para separar responsabilidades por módulo e evitar um `app.py` grande demais.
- Foi criada a tabela auxiliar `movimentacoes` para alimentar o dashboard com últimas atualizações.
- Foi criada a tabela auxiliar `historico_chips` para preservar o histórico de uso de cada chip.

## Como adicionar um novo campo ao banco

1. Adicione a nova coluna na tabela correspondente dentro de `models.py`.
2. Mantenha a mesma coluna tanto no bloco de SQLite quanto no de PostgreSQL.
3. Se o campo for da tabela `aparelhos`, atualize também a lista `APARELHO_FIELDS` em `routes/inventario.py`.
4. Inclua o campo no formulário HTML adequado dentro de `templates/`.
5. Se a base já existir, rode manualmente um `ALTER TABLE` no banco em uso.
6. Se a planilha de origem também tiver esse campo, atualize `TABLE_COLUMNS` em `importar_planilha.py`.

## Como adicionar uma nova página

1. Crie um novo arquivo em `routes/` com um `Blueprint`.
2. Registre o blueprint em `routes/__init__.py`.
3. Crie o template HTML correspondente em `templates/`.
4. Adicione o link de navegação em `templates/base.html`.
5. Se a página consultar dados, use os helpers de `database.py`.

## Como fazer backup dos dados

- Se estiver usando SQLite, feche a aplicação para garantir um snapshot estável.
- No SQLite, copie o arquivo `inventario.db`, que fica dentro da pasta do projeto.
- No PostgreSQL, faça backup com `pg_dump`.
- Guarde também a planilha original e eventuais exportações para auditoria.

Exemplos:

```powershell
Copy-Item .\inventario.db .\backup\inventario_$(Get-Date -Format yyyyMMdd_HHmmss).db
```

```powershell
pg_dump "$env:DATABASE_URL" > .\backup\inventario_$(Get-Date -Format yyyyMMdd_HHmmss).sql
```

## Fluxos implementados

- Dashboard com totais, aparelhos por unidade, status macro e últimas movimentações.
- Inventário com paginação, busca, filtros, cadastro, edição, ficha e exportação.
- Gestão de chips com filtro, vínculo com aparelho e histórico de uso.
- Estoque com movimentação para inventário e retorno do inventário para estoque.
- Devolvidos com cadastro e envio para estoque ou descarte.
- Descarte com cadastro, consulta por unidade e período, e exportação.
- Colaboradores com busca por nome ou matrícula e aparelhos vinculados.
- Grupos WhatsApp com resumo e lista de integrantes.

## Importação da planilha

O script `importar_planilha.py` tenta importar as abas principais mapeando as primeiras colunas de cada aba para as colunas do banco. Ele ignora linhas vazias e alguns cabeçalhos simples.

Observação importante:

- Como a estrutura real das abas pode variar na ordem ou quantidade de colunas, pode ser necessário ajustar o dicionário `TABLE_COLUMNS` após o primeiro teste com a planilha real.

## Comandos de execução

### 1. Clonar o repositório e criar o ambiente virtual Python

```powershell
git clone <URL-DO-SEU-REPOSITORIO>
cd inventario-ti
python -m venv .venv
```

### 2. Ativar o ambiente virtual

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependências

```powershell
pip install -r requirements.txt
```

### 4. Configurar ambiente

```powershell
Copy-Item .env.example .env
```

### 5. Criar o banco e as tabelas

#### Opção A: SQLite local

```powershell
python -c "from app import create_app; create_app(); print('Banco SQLite e tabelas criados com sucesso.')"
```

#### Opção B: PostgreSQL

```powershell
$env:DATABASE_URL="postgresql://USUARIO:SENHA@HOST:5432/inventario_ti"
python -c "from app import create_app; create_app(); print('Banco PostgreSQL e tabelas criados com sucesso.')"
```

### 6. Rodar o script de importação da planilha

Se estiver usando PostgreSQL, mantenha a variável `DATABASE_URL` definida antes de rodar:

```powershell
python importar_planilha.py
```

### 7. Iniciar o servidor local

```powershell
python app.py
```

Abra `http://127.0.0.1:5000` no navegador.

## Execução com Docker

1. Copie `.env.example` para `.env` e configure `SECRET_KEY`.
2. Garanta que `openedge.jar` esteja na raiz caso use a integração OpenEdge.
3. Execute:

```powershell
docker compose up --build
```

O sistema ficará disponível em `http://localhost:5000`.

## Preparação para GitHub

- Arquivos de credenciais (`.env`), bancos locais, caches e planilhas temporárias já são ignorados pelo Git.
- As migrações em `migrations/` são código-fonte e devem ser versionadas.
- Antes de tornar o repositório público, confirme se o `openedge.jar` pode ser redistribuído. Caso não possa, mantenha-o apenas fora do repositório e forneça-o no processo de deploy.
