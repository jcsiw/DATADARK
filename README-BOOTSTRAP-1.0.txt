DATADARK SITE BOOTSTRAP 1.0 - REV12

DATADARK Tecnologia — Site Bootstrap 1.0
========================================

OBJETIVO
--------
Versão independente do Mobirise, construída com HTML5, Bootstrap 5.3.8 (CSS)
e arquivos próprios da DATADARK.

ESTRUTURA PRINCIPAL
-------------------
index.html
assets/bootstrap/css/bootstrap.min.css
assets/css/datadark.css
assets/js/datadark.js
assets/images/

TESTE LOCAL
-----------
Recomendado: abrir um terminal dentro desta pasta e executar:

python3 -m http.server 8080

Depois abra no navegador:

http://localhost:8080

O site também pode ser aberto diretamente pelo arquivo index.html, mas o servidor
local representa melhor o comportamento que terá no GitHub Pages.

ARQUIVOS PARA EDITAR
--------------------
1. index.html
   Textos, seções, links, imagens e metadados SEO.

2. assets/css/datadark.css
   Cores, tamanhos, espaçamentos, layout e responsividade.

3. assets/js/datadark.js
   Menu móvel, formulário Formspree, Analytics e consentimento.

OBSERVAÇÕES
-----------
- Nenhum arquivo do Mobirise é necessário.
- Nenhum jQuery é utilizado.
- Nenhum npm ou processo de build é necessário.
- O formulário envia os dados pelo Formspree e é compatível com GitHub Pages.
- O Google Analytics é carregado apenas após consentimento e somente quando o
  hostname termina em datadark.com.br. Testes em localhost não contaminam o GA4.

HISTÓRICO DAS ETAPAS VALIDADAS
------------------------------
REV2 - FORMULÁRIO FORMSPREE
- Endpoint: https://formspree.io/f/xjybglyk
- Envio assíncrono via fetch, com fallback HTML POST.
- Mensagens de sucesso/erro na própria página.
- Honeypot _gotcha para filtragem básica de spam.

REV3 - HOME / SERVIÇOS EM DESTAQUE
- HOME/HERO com ajustes responsivos aprovados.
- Serviços com grade 3/2/1, cards uniformes e ícones padronizados.
- Conteúdo dos 9 serviços preservado.

REV5 - SOLUÇÕES / TECNOLOGIAS
- 10 cards reconstruídos em HTML/CSS.
- Ícones vetoriais inline e textos editáveis.
- Layout final validado em 5 colunas no desktop.

REV6 - SOBRE A DATADARK TECNOLOGIA
- Seção institucional redesenhada sem alterar as áreas já validadas.
- Imagem original preservada e valorizada em painel próprio.
- Hierarquia textual aprimorada com apresentação institucional objetiva.
- Três pilares visuais: Suporte técnico, Infraestrutura e Segurança/continuidade.
- Botão de contato integrado à seção existente.
- Layout responsivo para desktop, tablet e celular.

REV7 - ÁREA DE ATENDIMENTO
- Seção de atendimento redesenhada com modalidades Presencial e Remoto.
- Cidades presenciais organizadas em etiquetas compactas.
- CTA de atendimento e acesso ao WhatsApp preservados.

REV8 - BOTÃO SOLICITAR ATENDIMENTO
- O botão "Solicitar atendimento" da Área de Atendimento abre diretamente o Portal DATADARK.
- Destino: https://www.datadark.com.br/portal/
- Nenhuma outra seção foi alterada.

VERSÃO
------
Bootstrap 1.0 REV12 — 08/08/2026

REV9
- Seção Portal DATADARK reconstruída em HTML/CSS responsivo.
- Arte portal-imagens.png mantida apenas como elemento visual, com CTA real em HTML.
- Recursos do portal apresentados de forma editável e acessível.
- Imagem da área de contato preservada na versão validada após a REV8.

REV10 - PORTAL DATADARK
- Seção Portal visualmente validada.
- Texto, recursos e CTA permanecem em HTML independente da arte lateral.
- Imagem lateral limpa, sem menu ou conteúdo duplicado do próprio site.

REV11 - RODAPÉ FINAL
- Rodapé institucional reconstruído em HTML/CSS.
- Identificação DATADARK, navegação, modalidades de atendimento e contatos.
- Links diretos para Portal, WhatsApp, telefone e e-mail.
- CNPJ, copyright, crédito de desenvolvimento e retorno ao topo.
- Layout responsivo sem novas dependências.


REV12 - AJUSTE FINAL DO RODAPÉ
- Endereço físico removido do rodapé por validação do projeto.
- Telefone, e-mail, CNPJ, atalhos, Portal, WhatsApp e demais itens preservados.
