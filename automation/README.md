# Automação gratuita: GitHub → Buffer → Instagram / TikTok

Esta rotina **não altera o site**, não usa Metricool e não exige abrir o Buffer para cada vídeo.

## Estado inicial
- Vídeo aprovado: `assets/reels10-lanchonetes-cafeterias-aprovado.mp4`.
- Destinos: Instagram e TikTok do Kit Controle Fácil, identificados pelo ID exato do canal Buffer.
- `automation/posts.json`: catálogo explícito de vídeos aprovados. Nenhum outro MP4 será publicado automaticamente por estar na pasta `assets`.
- `.github/workflows/buffer-publicar.yml`: rotina diária às **09:00 (horário de Brasília, UTC-3)** e início manual.
- `automation/buffer_publish.py`: valida MP4 local/público, consulta histórico do Buffer, bloqueia duplicatas pelo nome do vídeo, identificador e legenda, limita a um vídeo novo por canal e execução.

## Ativação (uma única vez)
1. Entre no Buffer e acesse **Settings → API**: https://publish.buffer.com/settings/api
2. Crie uma **personal API key**. A API está disponível no plano Free.
3. No GitHub, abra a criação de segredo: https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/settings/secrets/actions/new
4. Em **Name**, digite exatamente `BUFFER_API_KEY`; em **Secret**, cole a chave. Clique em **Add secret**.
5. Vá em https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/actions/workflows/buffer-publicar.yml
6. Use **Run workflow** com **dry_run marcado** para fazer a verificação sem publicação.
7. Confira os logs. Se o resultado for válido e sem duplicações, use **Run workflow** com **dry_run desmarcado** para colocar o Reels 10 nas filas do Buffer.
8. Em seguida, a execução diária continuará conferindo duplicações sem adicionar o mesmo Reels de novo.

**Não envie a chave API em comentários, issues, capturas públicas nem neste arquivo.** Deixe-a exclusivamente em GitHub Actions Secrets.

## Cuidados
- Se a chave ainda não tiver sido instalada, a automação exibe `NÃO ATIVADO` e não publica nada.
- Se não conseguir consultar canais, histórico, MP4 ou a API, a publicação é bloqueada.
- A conferência de duplicações funciona para conteúdos identificáveis pelo nome do MP4 ou termos cadastrados. Publicações manuais sem esses sinais podem precisar de auditoria humana.
- O Buffer decide os horários reais na fila. `addToQueue` não significa publicação instantânea.
- Novos vídeos exigem inclusão explícita no manifesto com `approved: true`; a automação **não** publica indiscriminadamente os outros vídeos existentes.
- A rotina não apaga, modifica nem atualiza posts existentes ou arquivos de site.


## Diagnóstico da primeira execução — 02/11/2026

A execução de homologação disparada automaticamente por uma alteração no workflow validou a sintaxe Python e o catálogo, mas bloqueou a integração porque a variável `BUFFER_API_KEY` estava vazia no ambiente do GitHub Actions. Isso não significa que a chave não exista no Buffer: é necessário cadastrá-la também como **Repository secret** com o nome exato `BUFFER_API_KEY`.

A execução diária está **ativa** e verifica/publica somente conteúdos explicitamente aprovados no catálogo. A opção manual `dry_run=true` faz apenas simulação. A execução sem `dry_run` coloca posts na fila do Buffer.


## Homologação e ativação verificadas — 02/11/2026

- A chave em GitHub Secrets foi reconhecida na execução [41556497756](https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/actions/runs/41556497756).
- A execução [41556668653](https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/actions/runs/41556668653) criou o Reels 10 no Buffer, uma vez para cada canal: Instagram `6ae931e85d11dd638e97506f` (03/11/2026 às 18h41 de Brasília) e TikTok `6ae931e9186a5afbce75f0ae` (03/11/2026 às 06h49 de Brasília).
- A segunda execução [41556745209](https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/actions/runs/41556745209) encontrou os posts existentes e ignorou ambos, validando o bloqueio de duplicações.
- Esses status são agendamentos do Buffer, não comprovantes de publicação final nas redes sociais. Verifique a aba Sent após o horário.


## Auditoria automática de publicação

A rotina de auditoria `.github/workflows/buffer-auditoria.yml` roda separadamente do publicador, diariamente às **09h30 e 20h30 de Brasília**. Ela usa o mesmo secret `BUFFER_API_KEY` e executa `automation/buffer_audit.py`, sem criar ou alterar posts.

- `AGUARDANDO`: o Buffer ainda mantém o vídeo na fila, antes de vencer o horário e a tolerância de 2 horas.
- `OK`: o Buffer confirma o estado `sent`; quando disponível, o relatório traz a URL pública.
- `ERRO`: há falha no Buffer, publicação ainda não enviada após a tolerância, vídeo ausente ou possível duplicação. A execução do GitHub Actions termina em falha.

Relatório no GitHub: https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/actions/workflows/buffer-auditoria.yml

Primeira execução: https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/actions/runs/41557278942 — **sucesso**. Os seis testes automatizados passaram e o Buffer confirmou o Reels 10 agendado no Instagram e TikTok.

**Limitação:** `sent` confirma publicação conforme a API do Buffer; indisponibilidade de URL pública ou falhas de indexação da rede podem exigir confirmação no destino. O GitHub pode atrasar execuções programadas.

A automação monitora exclusivamente conteúdos autorizados em `automation/posts.json`. Para o próximo vídeo, será necessária aprovação explícita do conteúdo, da legenda e dos canais antes de adicioná-lo com `approved: true`.

## Campanha de 03/11/2026: conteúdos inéditos (10 em 10 minutos)

Programação de 14 posts aceita no Buffer pela execução https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/actions/runs/41558874538.

- **TikTok, 8 vídeos:** Reels 03 (09h00), 04 (09h10), 05 (09h20), 06 (09h30), 07 (09h40), 08 (09h50), 11 (10h00) e vídeo de apresentação com legendas corrigidas (10h10).
- **Instagram, 6 conteúdos:** Reels 06 (09h00), Reels 07 (09h10), Reels 08 (09h20), Reels 11 (09h30), Story 11 (09h40) e post estático original de checklist financeiro (09h50).
- Horário de Brasília (UTC-3), 3 de novembro de 2026.
- O Reels 10 já possuía agendamentos em ambas as redes, por isso não foi reprogramado.
- A demonstração prática já constava como enviada em ambos os canais; outros temas cobertos no histórico do Instagram (estoque, barbearias, lojas/apresentação) foram excluídos por precaução para evitar posts semanticamente repetidos.
- O controle `automation/campanha-03nov-state.json` registra os 14 IDs criados no Buffer. A execução seguinte em modo seguro não criou novas cópias.
- A auditoria de rotina verifica o Reels 10 e os 14 IDs da campanha. Primeira execução de auditoria: https://github.com/duarteleonardo692-eng/kit-controle-facil-midia/actions/runs/41559149834 — 14 agendados e 0 falhas.
- A rotina pontual `.github/workflows/campanha-10min.yml` foi desativada para novos envios (`DRY_RUN=true`) após registrar a campanha; os horários permanecem no Buffer.
- Limitação do plano Free: máximo de 10 posts na fila por canal; foram utilizados 9 slots no TikTok, 7 no Instagram, incluindo Reels 10. A plataforma pode recusar publicações posteriores por outros motivos; confira a auditoria no dia.
