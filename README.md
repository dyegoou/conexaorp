# Bot Discord Profissional

Bot modular em Python com `discord.py`, slash commands, embeds e autorização
baseada em cargos do servidor.

## Comandos

- `/ping` — verifica se o bot está respondendo e exibe a latência.
- `/ajuda` — lista os comandos disponíveis.
- `/status` — exibe o status operacional; restrito aos cargos configurados.
- `/pagamento` — publica uma confirmação de pagamento para um usuário ou
  cargo; restrito aos cargos configurados.
- `$sync` — reinicia e sincroniza o bot com um aviso técnico em inglês;
  disponível somente para o proprietário configurado.
- `$kick @usuário` — expulsa um membro do servidor; disponível somente para o
  proprietário configurado.
- `$setupwl` — publica manualmente o painel de whitelist no canal configurado;
  disponível somente para o proprietário.
- `/close` — fecha e remove o ticket atual; disponível para a staff.
- `/add` e `/remove` — gerenciam o acesso de pessoas ao ticket; disponíveis
  para a staff.

Os slash commands são sincronizados automaticamente no `setup_hook` e o
console registra quando a conexão estiver online.

## Configuração segura

O token nunca fica no código. Configure um Secret chamado `DISCORD_TOKEN` no
ambiente do projeto. Configure também `DISCORD_OWNER_ID` com o ID numérico do
proprietário do bot. Configure `DISCORD_PAYMENT_ROLE_ID` com o ID numérico do
único cargo autorizado a publicar pagamentos. Cargos autorizados para
`/status` podem ser alterados com a variável opcional `DISCORD_ADMIN_ROLES`,
usando nomes separados por vírgula.
Configure `DISCORD_PAYMENT_LOG_CHANNEL_ID` com o ID numérico do canal que
receberá os registros dos pagamentos.

O sistema de whitelist usa estas variáveis: `DISCORD_WHITELIST_PANEL_CHANNEL_ID`,
`DISCORD_WHITELIST_TICKET_CATEGORY_ID`, `DISCORD_WHITELIST_STAFF_ROLE_ID`,
`DISCORD_WHITELIST_UNVERIFIED_ROLE_ID`, `DISCORD_WHITELIST_VERIFIED_ROLE_ID`,
`DISCORD_WHITELIST_SECOND_ROLE_ID` e `DISCORD_WHITELIST_WEBSITE_URL`.
O painel é publicado automaticamente no canal configurado. O `$setupwl` pode
ser usado pelo proprietário para publicar uma nova cópia manualmente.
Todo novo membro recebe automaticamente o cargo `Unverified` assim que entra
no servidor. O bot precisa estar acima desse cargo na hierarquia do Discord e
ter a permissão **Manage Roles**.

Nos tickets, o botão **Reprovar** abre um formulário obrigatório para o motivo.
O motivo é salvo na embed do ticket e enviado por DM ao candidato. O botão
**Aprove** aplica os cargos configurados, remove `Unverified`, tenta atualizar
o nick para o nome do Roblox e envia as instruções por DM.

O bot precisa ser convidado com os escopos OAuth2 `bot` e
`applications.commands`. Para o `/status`, o usuário precisa ter um dos cargos
listados em `DISCORD_ADMIN_ROLES`.

Para o `$sync`, ative **Message Content Intent** em **Discord Developer Portal →
Bot → Privileged Gateway Intents**. Para enviar DMs a todos os membros de um
cargo, ative também **Server Members Intent**. O prefixo do bot é `$`.

O `/pagamento` só funciona para membros que tenham o cargo com o ID definido
em `DISCORD_PAYMENT_ROLE_ID`. Ao pagar um usuário, ele recebe uma DM. Ao pagar
um cargo, cada membro humano desse cargo recebe uma DM. O registro público é
enviado para o canal definido em `DISCORD_PAYMENT_LOG_CHANNEL_ID`, enquanto
o canal onde o comando foi usado recebe apenas uma confirmação privada.

### Exemplo de pagamento

O comando aceita um valor personalizado e exatamente um destinatário. O valor
é convertido automaticamente para reais brasileiros:

```text
/pagamento valor:10 usuario:@Pessoa
/pagamento valor:10,50 cargo:@Apoiadores observacao:Bônus mensal
```

O registro é uma mensagem em embed no estilo de holerite, com Conexão RP, valor
em destaque, data no horário de Brasília, status aprovado, quem confirmou e os
emojis de pagamento. Para pagamentos a um cargo, o cargo contemplado também é
exibido. A mesma estrutura é enviada por DM para o usuário ou para cada membro
humano do cargo.

Exemplos de conversão: `10` vira `R$ 10,00`, `10,5` vira `R$ 10,50` e
`1250.75` vira `R$ 1.250,75`.

## Execução

```bash
python -m discord_bot
```

Ou, usando o script do projeto:

```bash
discord-bot
```

Sem `DISCORD_TOKEN`, o processo encerra com uma mensagem clara e não tenta
iniciar uma conexão.