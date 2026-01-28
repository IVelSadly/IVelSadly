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
- `WHATSAPP_APP_SECRET`: App Secret do app da Meta (usado para validar `X-Hub-Signature-256`)

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

Regras do MVP:

- Ignora payloads sem mensagens.
- Ignora mensagens que não são texto.
- Protege contra reprocessamento (idempotência por `message_id`).
- Aplica rate limit simples (por IP e por `wa_id`).
- Retorna 200 rapidamente e envia a resposta em background.

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

## Validação de assinatura (X-Hub-Signature-256)

O webhook valida a assinatura HMAC SHA-256 com `WHATSAPP_APP_SECRET`. O header esperado é:

```
X-Hub-Signature-256: sha256=<hash>
```

Para gerar a assinatura localmente (exemplo), use:

```bash
BODY='{"test":"payload"}'
APP_SECRET='your_app_secret_here'
SIGNATURE=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$APP_SECRET" | sed 's/^.* //')

echo "X-Hub-Signature-256: sha256=$SIGNATURE"
```

Exemplo de teste com `curl`:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$BODY"
```

## Logs e debug

- O servidor loga apenas informações mínimas e nunca imprime tokens ou payload completo.
- Cada requisição gera um `request_id` retornado na resposta JSON para facilitar o rastreio.

## Observações importantes

- Você precisa habilitar o WhatsApp Cloud API e configurar o webhook no Meta Developers.
- O token de verificação é escolhido por você e deve coincidir no Meta e no `.env`.
- Para ambientes de produção, use HTTPS e proteja seus tokens.

## Próximos passos sugeridos (Passo 2+)

- Persistir mensagens recebidas (DB)
- Implementar filas/worker com Redis/SQS
- Verificação de assinatura reforçada com rotação de segredos
- Observabilidade (tracing/metrics)
