# API de campeonatos de jogos

Projeto de Desenvolvimento de API com Persistência e Arquitetura Distribuída. Implementa criação, listagem, consulta, atualização e exclusão de campeonatos, com persistência em PostgreSQL.

## Tecnologias e arquitetura

As duas opções implementadas são:

1. **API Gateway com balanceamento de carga e rate limit**, usando NGINX.
2. **Mensageria com Producer e Consumer**, usando RabbitMQ.

- Python, FastAPI e SQLAlchemy para a API e o acesso ao banco.
- PostgreSQL para persistência dos dados.
- NGINX como API Gateway, com balanceamento entre duas instâncias e limite de requisições.
- RabbitMQ para mensageria, com producer na API e consumer em processo separado.
- Docker Compose para execução dos serviços.

```text
Cliente → NGINX → api1 / api2 → PostgreSQL
                     ↓
                  RabbitMQ → Consumer
```

As duas instâncias compartilham o banco. O NGINX distribui as requisições por round-robin. O cabeçalho `X-Instancia` identifica quem respondeu. O limite é de 5 requisições por segundo por IP, com tolerância de 5 requisições excedentes; acima disso, o gateway retorna HTTP 429.

O banco compartilhado mantém os mesmos dados disponíveis para ambas as instâncias. O gateway centraliza o acesso e distribui a carga. A mensageria permite processar os eventos em um serviço separado da API. O Docker Compose reúne os componentes e suas dependências em uma configuração reproduzível.

## Execução

Requisito: Docker com Docker Compose e suporte a containers Linux.

No Windows, abra o Docker Desktop e aguarde o mecanismo iniciar antes de executar os comandos no PowerShell.

Na pasta do projeto:

```sh
docker compose up --build
```

- API: `http://localhost:8000/campeonatos`
- Documentação dos endpoints (Swagger): `http://localhost:8000/docs`
- Painel do RabbitMQ: `http://localhost:15672`

Endereços das instâncias dentro da rede Docker:

- API 1: `http://api1:8000/campeonatos`
- API 2: `http://api2:8000/campeonatos`

Os nomes `api1` e `api2` são acessíveis pelos containers na rede do Compose. Esses endereços não abrem diretamente no navegador do computador, pois as portas das instâncias não estão publicadas. No computador, use `http://localhost:8000/campeonatos`: o NGINX encaminha a requisição para uma das instâncias, identificada pelo cabeçalho `X-Instancia` da resposta.

As configurações padrão estão em `docker-compose.yml`. O arquivo `.env.example` contém as variáveis para personalização. O acesso padrão ao RabbitMQ é `estudante` / `estudante123`.

### Portas

| Serviço | Porta no container | Porta no computador |
| --- | --- | --- |
| NGINX (acesso à API e ao Swagger) | 80 | 8000 |
| API (cada instância) | 8000 | Somente rede interna Docker |
| PostgreSQL | 5432 | Somente rede interna Docker |
| RabbitMQ (mensagens) | 5672 | Somente rede interna Docker |
| RabbitMQ (painel) | 15672 | 15672 |

### Variáveis de ambiente

| Variável | Finalidade | Padrão |
| --- | --- | --- |
| `POSTGRES_DB` | Nome do banco | `campeonatos` |
| `POSTGRES_USER` | Usuário do banco | `estudante` |
| `POSTGRES_PASSWORD` | Senha do banco | `estudante123` |
| `RABBITMQ_USER` | Usuário do RabbitMQ | `estudante` |
| `RABBITMQ_PASSWORD` | Senha do RabbitMQ | `estudante123` |

O arquivo `.env` é opcional. Para personalizar os valores, copie `.env.example` para `.env` na raiz do projeto e edite antes da primeira inicialização. No PowerShell:

```powershell
Copy-Item .env.example .env
```

`INSTANCE_NAME` é definido pelo Compose como `api1` ou `api2` para identificar cada instância. As credenciais padrão são destinadas à execução local. Alterar as variáveis do PostgreSQL não altera as credenciais de um volume já inicializado.

### Logs e encerramento

Para acompanhar as mensagens:

```sh
docker compose logs -f consumer
```

Para encerrar os serviços:

```sh
docker compose down
```

Os volumes preservam os dados ao encerrar e recriar os containers.

## Endpoints

| Método | Rota | Descrição | Sucesso |
| --- | --- | --- | --- |
| POST | `/campeonatos` | Cria um campeonato | 201 |
| GET | `/campeonatos` | Lista os campeonatos | 200 |
| GET | `/campeonatos/{id}` | Consulta por ID | 200 |
| PUT | `/campeonatos/{id}` | Atualiza todos os campos editáveis | 200 |
| DELETE | `/campeonatos/{id}` | Exclui um campeonato | 204 |
| GET | `/health` | Verifica o banco e identifica a instância | 200 |

IDs inexistentes retornam 404. Dados inválidos retornam 422.

## Dados do campeonato

Exemplo de corpo para POST e PUT:

```json
{
  "nome": "Campeonato FIFA 26",
  "jogo": "FIFA 26",
  "data": "2026-09-20",
  "premiacao": 300,
  "status": "aberto"
}
```

Todos os campos são obrigatórios. O ID é gerado pelo banco. Nome e jogo não podem ser vazios e aceitam até 120 e 80 caracteres, respectivamente. A data usa o formato `AAAA-MM-DD`. A premiação aceita valores de zero a 9.999.999.999,99, com até duas casas decimais. O status aceita `aberto`, `em_andamento` ou `encerrado`. A premiação é retornada como string para preservar a precisão decimal.

## CRUD pelo terminal (PowerShell)

Com os serviços em execução, abra outro PowerShell e execute os blocos em ordem, no mesmo terminal. As variáveis são reutilizadas nas operações seguintes. Execute um bloco por vez; se receber HTTP 429, aguarde alguns segundos antes de repetir a requisição.

### Criar — POST

```powershell
$ErrorActionPreference = 'Stop'
$base = 'http://localhost:8000'
$dados = @{
    nome = 'Campeonato da aula'
    jogo = 'FS25'
    data = '2026-09-15'
    premiacao = 1000
    status = 'aberto'
}
$corpo = [System.Text.Encoding]::UTF8.GetBytes(($dados | ConvertTo-Json))
$novo = Invoke-RestMethod -Uri "$base/campeonatos" -Method Post -ContentType 'application/json; charset=utf-8' -Body $corpo
$campeonatoId = $novo.id
$novo | Format-List
```

O ID gerado pelo banco fica em `$campeonatoId`. A criação retorna HTTP 201.

### Listar — GET

```powershell
Invoke-RestMethod -Uri "$base/campeonatos" -Method Get | Format-Table
```

### Consultar por ID — GET

```powershell
Invoke-RestMethod -Uri "$base/campeonatos/$campeonatoId" -Method Get | Format-List
```

Para consultar outro registro, atribua seu ID a `$campeonatoId` antes da requisição.

### Atualizar — PUT

O PUT exige todos os campos editáveis. O objeto `$dados` mantém os campos definidos na criação:

```powershell
$dados.nome = 'Campeonato atualizado'
$dados.premiacao = 2000
$dados.status = 'em_andamento'
$corpo = [System.Text.Encoding]::UTF8.GetBytes(($dados | ConvertTo-Json))
Invoke-RestMethod -Uri "$base/campeonatos/$campeonatoId" -Method Put -ContentType 'application/json; charset=utf-8' -Body $corpo | Format-List
```

Consulte novamente pelo ID para conferir os dados atualizados. A atualização retorna HTTP 200.

### Excluir — DELETE

O comando exclui o registro identificado por `$campeonatoId`:

```powershell
Invoke-RestMethod -Uri "$base/campeonatos/$campeonatoId" -Method Delete
```

A exclusão retorna HTTP 204, sem conteúdo no terminal. Liste novamente para conferir:

```powershell
Invoke-RestMethod -Uri "$base/campeonatos" -Method Get | Format-Table
```

Uma consulta pelo ID excluído retorna HTTP 404. Para acompanhar os eventos de criação e exclusão, use `docker compose logs -f consumer` em outro terminal na pasta do projeto.

## Mensageria

- `campeonato_criado`: recebe os dados após a criação de um campeonato.
- `campeonato_excluido`: recebe os dados após a exclusão de um campeonato.

O consumer escuta as duas filas, imprime o nome do campeonato e confirma o processamento. As filas são duráveis e as mensagens são persistentes. Consultas e atualizações não publicam eventos.

A gravação no banco e a publicação no RabbitMQ são operações separadas. Se a publicação falhar após a gravação, a operação no banco permanece concluída e a API retorna `X-Evento-Status: falhou`, sem reenvio automático. Quando a publicação é confirmada, retorna `X-Evento-Status: publicado`.
