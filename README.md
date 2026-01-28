# WhatsApp Bot MVP — Passo 1 (FastAPI + WhatsApp Cloud API)

Este passo cria um bot mínimo com FastAPI que valida o webhook da Meta e responde mensagens de texto com um eco. Ele usa a WhatsApp Cloud API (Graph API) para enviar a resposta.

## Estrutura do projeto

```
/app
  main.py
  config.py
  whatsapp.py
.env.example
requirements.txt
README.md
```

## Requisitos

- Python 3.11+
- Conta Meta Developers com WhatsApp Cloud API habilitada

## Configuração do ambiente

1) Crie um virtualenv e instale dependências:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Copie o `.env.example` para `.env` e preencha:

```bash
cp .env.example .env
```

Variáveis usadas:

- `WHATSAPP_ACCESS_TOKEN`: token de acesso do app (Meta)
- `WHATSAPP_PHONE_NUMBER_ID`: ID do número de telefone no WhatsApp Cloud API
- `WHATSAPP_VERIFY_TOKEN`: token arbitrário para validação do webhook (você define)

## Como rodar localmente

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API ficará disponível em `http://localhost:8000`.

## Expondo localmente com ngrok

```bash
ngrok http 8000
```

O ngrok exibirá uma URL pública como:

```
https://abcd-1234.ngrok-free.app
```

## Configurar o webhook no Meta Developers

No painel do seu app (WhatsApp > Configuration):

- **Callback URL**: `https://abcd-1234.ngrok-free.app/webhook`
- **Verify token**: use o mesmo valor de `WHATSAPP_VERIFY_TOKEN` do `.env`

A Meta fará uma requisição GET para validar o webhook:

```
GET /webhook?hub.mode=subscribe&hub.verify_token=SEU_TOKEN&hub.challenge=12345
```

Se o token estiver correto, o endpoint retorna o `hub.challenge`.

## Endpoints

### GET /webhook

Validação do webhook do Meta (retorna o `hub.challenge`).

### POST /webhook

Recebe eventos do WhatsApp e responde mensagens de texto com:

```
Recebido: <mensagem>
```

Mensagens sem texto ou eventos que não são mensagens são ignorados.

## Exemplo de payload recebido (POST /webhook)

```json
{
  "entry": [
    {
      "changes": [
        {
          "value": {
            "contacts": [
              {
                "wa_id": "5511999999999"
              }
            ],
            "messages": [
              {
                "from": "5511999999999",
                "id": "wamid.HBg...",
                "timestamp": "1700000000",
                "type": "text",
                "text": {
                  "body": "Olá, bot!"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

### Como o código extrai os dados

- **wa_id**: `message["from"]` (ou `contacts[0].wa_id` como fallback)
- **texto**: `message["text"]["body"]`

## Observações importantes

- Você precisa habilitar o WhatsApp Cloud API e configurar o webhook no Meta Developers.
- O token de verificação é escolhido por você e deve coincidir no Meta e no `.env`.
- Para ambientes de produção, use HTTPS e proteja seus tokens.

## Próximos passos sugeridos (Passo 2+)

- Persistir mensagens recebidas (DB)
- Implementar filas/worker
- Autenticação/verificação de assinatura
