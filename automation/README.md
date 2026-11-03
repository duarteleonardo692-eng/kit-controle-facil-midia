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
