# API de campeonatos de jogos

Projeto de Desenvolvimento de API com Persistência e Arquitetura Distribuída. Implementa criação, listagem, consulta, atualização e exclusão de campeonatos, com persistência em PostgreSQL.

## Tecnologias e arquitetura

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

## Execução

Requisito: Docker com Docker Compose e suporte a containers Linux.

Na pasta do projeto:

```sh
docker compose up --build
```

- API: `http://localhost:8000/campeonatos`
- Documentação dos endpoints (Swagger): `http://localhost:8000/docs`
- Painel do RabbitMQ: `http://localhost:15672`

As configurações padrão estão em `docker-compose.yml`. O arquivo `.env.example` contém as variáveis para personalização. O acesso padrão ao RabbitMQ é `estudante` / `estudante123`.

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

## Mensageria

- `campeonato_criado`: recebe os dados após a criação de um campeonato.
- `campeonato_excluido`: recebe os dados após a exclusão de um campeonato.

O consumer escuta as duas filas, imprime o nome do campeonato e confirma o processamento. As filas são duráveis e as mensagens são persistentes. Consultas e atualizações não publicam eventos.

A gravação no banco e a publicação no RabbitMQ são operações separadas. Se a publicação falhar após a gravação, a operação no banco permanece concluída e a API retorna `X-Evento-Status: falhou`, sem reenvio automático. Quando a publicação é confirmada, retorna `X-Evento-Status: publicado`.
