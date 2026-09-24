# Bot Discord Profissional

Bot modular em Python com slash commands, embeds e permissões baseadas nos
cargos do Discord.

## Run & Operate

- `python -m discord_bot` — inicia o bot.
- `discord-bot` — inicia pelo script definido no `pyproject.toml`.
- Workflow `Discord Bot` — executa o processo continuamente no console.
- `python -m compileall -q discord_bot main.py` — valida a sintaxe Python.

## Configuração

- Obrigatório: Secret `DISCORD_TOKEN`.
- Obrigatório: `DISCORD_OWNER_ID`, ID numérico autorizado a executar `$rr`.
- Obrigatório: `DISCORD_PAYMENT_ROLE_ID`, ID numérico do cargo que pode usar
  `/pagamento`.
- Opcional: `DISCORD_ADMIN_ROLES`, com cargos separados por vírgula.
- Nunca grave tokens em arquivos, logs ou código.

## Stack

- Python 3.13
- `discord.py` 2.7
- Slash commands via `discord.app_commands`

## Onde as coisas ficam

- `discord_bot/main.py` — entrada, validação de configuração e inicialização.
- `discord_bot/bot.py` — classe do bot, carregamento dos cogs e sincronização.
- `discord_bot/cogs/` — comandos organizados por domínio.
- `discord_bot/cogs/owner.py` — comando prefixado `$rr`, restrito ao proprietário.
- `discord_bot/checks.py` — checks reutilizáveis de autorização por cargo.
- `discord_bot/embeds.py` — identidade e fábrica dos embeds.
- `.env.example` — referência de variáveis sem valores sensíveis.
- `README.md` — configuração do bot no Discord e lista de comandos.

## Decisões de arquitetura

- O token é lido somente por `DISCORD_TOKEN` e a inicialização falha
  explicitamente quando ele não existe.
- Slash commands são registrados no `setup_hook`, antes do evento online.
- Comandos ficam em cogs para permitir novos módulos sem crescer o arquivo
  principal.
- `/status` usa uma check baseada em nomes de cargos configuráveis; `/ping` e
  `/ajuda` são públicos.

## Produto

O bot oferece `/ping`, `/ajuda`, `/status`, `/pagamento` e `$rr`, com respostas
em embeds, sincronização automática dos comandos e logs de conexão no console.

## Gotchas

- O bot precisa ser convidado com os escopos `bot` e `applications.commands`.
- O **Message Content Intent** precisa estar ativo no Discord Developer Portal
  para o `$rr` funcionar.
- O **Server Members Intent** precisa estar ativo para o `/pagamento` localizar
  todos os membros do cargo e enviar as DMs.
- Sem um cargo listado em `DISCORD_ADMIN_ROLES`, `/status` responde com acesso
  não autorizado.
- Avisos sobre suporte a voz do `discord.py` são esperados: este bot usa apenas
  slash commands e não precisa de recursos de voz.