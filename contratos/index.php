<?php
// DATADARK - Contrato de Prestação de Serviços de TI
// Versão 1.0 - preenchimento e impressão local. Sem gravação em banco de dados.
?>
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Contrato de Prestação de Serviços - DATADARK</title>
<style>
    :root {
        --azul: #15469b;
        --azul-claro: #6697e8;
        --texto: #262626;
        --borda: #7ca4e8;
        --fundo: #eef2f7;
    }

    * { box-sizing: border-box; }

    html, body {
        margin: 0;
        padding: 0;
        background: var(--fundo);
        color: var(--texto);
        font-family: "Times New Roman", Times, serif;
    }

    .toolbar {
        position: sticky;
        top: 0;
        z-index: 10;
        display: flex;
        justify-content: center;
        gap: 10px;
        padding: 12px;
        background: rgba(24, 31, 43, .96);
        box-shadow: 0 2px 10px rgba(0,0,0,.18);
    }

    .toolbar button {
        border: 0;
        border-radius: 7px;
        padding: 10px 18px;
        font: 600 14px Arial, sans-serif;
        cursor: pointer;
    }

    .btn-print { background: #1565c0; color: #fff; }
    .btn-clear { background: #fff; color: #222; }

    .sheet {
        position: relative;
        width: 210mm;
        min-height: 297mm;
        margin: 10mm auto;
        padding: 12mm 13mm 12mm;
        background: #fff;
        box-shadow: 0 2px 20px rgba(0,0,0,.13);
        page-break-after: always;
        overflow: hidden;
    }

    .sheet:last-child { page-break-after: auto; }

    .header-img {
        display: block;
        width: 100%;
        height: auto;
        margin: 0 0 5mm;
    }

    h1 {
        margin: 1mm 0 1mm;
        text-align: center;
        color: var(--azul);
        font-size: 17pt;
        line-height: 1.06;
        font-weight: 700;
        text-transform: uppercase;
        border-bottom: 1.3pt solid var(--azul);
        padding-bottom: 1.5mm;
    }

    h2 {
        margin: 7mm 0 2mm;
        color: var(--azul);
        font-size: 14.2pt;
        line-height: 1.05;
        font-weight: 700;
        text-transform: uppercase;
        border-bottom: .8pt solid var(--azul-claro);
        padding-bottom: 1.2mm;
    }

    h3 {
        margin: 2.5mm 0 1.5mm;
        color: var(--azul);
        font-size: 13.5pt;
        font-weight: 700;
    }

    p, li, label, td {
        font-size: 11.4pt;
        line-height: 1.25;
    }

    p { margin: 1.3mm 0; }

    .line-field {
        display: flex;
        align-items: baseline;
        gap: 2mm;
        margin: 1.1mm 0;
        font-size: 11.4pt;
    }

    .line-field > label { white-space: nowrap; }

    input[type="text"], input[type="email"], input[type="tel"], input[type="date"], input[type="number"], textarea {
        font-family: "Times New Roman", Times, serif;
        color: #111;
        font-size: 11.2pt;
        background: transparent;
        outline: none;
    }

    .line-input {
        flex: 1;
        min-width: 0;
        border: 0;
        border-bottom: .65pt solid #8f979f;
        padding: 0 1mm .6mm;
    }

    textarea {
        width: 100%;
        resize: none;
        border: .8pt solid var(--borda);
        padding: 2.5mm;
        line-height: 1.3;
    }

    .services-box { height: 36mm; }
    .obs-box { height: 14mm; }

    .two-cols {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 5mm;
    }

    .service-list {
        margin: 1mm 0 0 5mm;
        padding: 0;
    }

    .service-list li { margin: .8mm 0; }

    .date-grid, .value-table, .signature-grid, .company-box {
        width: 100%;
        border-collapse: collapse;
    }

    .date-grid td, .value-table td, .signature-grid td, .company-box td {
        border: .8pt solid var(--borda);
        vertical-align: top;
        padding: 2.2mm;
    }

    .date-grid input,
    .value-table input,
    .signature-grid input {
        width: 100%;
        border: 0;
        border-bottom: .65pt solid #8f979f;
        padding: .7mm 1mm;
    }

    .value-table td:first-child { width: 50%; }
    .value-total-label {
        background: var(--azul);
        color: #fff;
        font-weight: 700;
    }
    .value-total { font-weight: 700; }

    .payment-box {
        border: .8pt solid var(--borda);
        padding: 6mm 3.5mm 3mm;
        min-height: 68mm;
    }

    .payment-item {
        display: flex;
        align-items: center;
        gap: 2mm;
        margin: 5mm 0;
        font-family: Arial, sans-serif;
        font-size: 9.8pt;
        color: #777;
    }

    input[type="checkbox"] {
        width: 4mm;
        height: 4mm;
        accent-color: var(--azul);
    }

    .payment-notes {
        display: flex;
        align-items: baseline;
        gap: 2mm;
        margin-top: 8mm;
    }

    .payment-notes input {
        flex: 1;
        border: 0;
        border-bottom: .65pt solid #888;
    }

    .guarantee-row {
        display: flex;
        align-items: baseline;
        gap: 2mm;
    }

    .guarantee-days {
        width: 22mm;
        border: 0;
        border-bottom: .65pt solid #8f979f;
        text-align: center;
    }

    .guarantee-list {
        columns: 3;
        column-gap: 10mm;
        margin: 1mm 0 0 5mm;
        padding: 0;
    }

    .guarantee-list li {
        break-inside: avoid;
        margin: 1mm 0;
    }

    .signature-intro {
        text-align: center;
        margin-top: 33mm;
        margin-bottom: 2mm;
    }

    .signature-grid td { width: 50%; height: 47mm; }
    .signature-title {
        text-align: center;
        color: var(--azul);
        font-size: 13.5pt;
        font-weight: 700;
        margin-bottom: 2mm;
    }
    .signature-center { text-align: center; }

    .company-box {
        position: absolute;
        left: 13mm;
        right: 13mm;
        bottom: 21mm;
        width: calc(100% - 26mm);
    }
    .company-box td { width: 50%; }
    .company-name { color: var(--azul); font-weight: 700; font-size: 12pt; }

    .footer {
        position: absolute;
        left: 13mm;
        right: 13mm;
        bottom: 6mm;
        text-align: center;
        color: #666;
        border-bottom: .6pt solid var(--azul-claro);
        padding-bottom: 1.2mm;
        font-size: 7.8pt;
    }

    .page1-content { padding-bottom: 50mm; }

    @page {
        size: A4 portrait;
        margin: 0;
    }

    @media print {
        html, body { background: #fff !important; }
        .toolbar { display: none !important; }
        .sheet {
            width: 210mm;
            height: 297mm;
            min-height: 297mm;
            margin: 0;
            box-shadow: none;
            page-break-after: always;
        }
        .sheet:last-child { page-break-after: auto; }
        input, textarea { color: #000 !important; }
        textarea { overflow: hidden; }
        input::placeholder, textarea::placeholder { color: transparent !important; }
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    @media screen and (max-width: 900px) {
        .sheet {
            width: calc(100% - 20px);
            min-height: auto;
            margin: 10px auto;
            padding: 18px;
        }
        .company-box, .footer { position: static; width: 100%; margin-top: 16px; }
        .two-cols { grid-template-columns: 1fr; gap: 0; }
        .guarantee-list { columns: 1; }
    }
</style>
</head>
<body>

<div class="toolbar">
    <button class="btn-print" type="button" onclick="window.print()">Imprimir / Salvar em PDF</button>
    <button class="btn-clear" type="button" onclick="limparFormulario()">Limpar campos</button>
</div>

<form id="contratoForm" autocomplete="off">

<section class="sheet">
    <img class="header-img" src="assets/cabecalho-datadark.png" alt="DATADARK Tecnologia">

    <div class="page1-content">
        <h1>Contrato de Prestação<br>de Serviços de Tecnologia da Informação</h1>
        <p>Pelo presente instrumento particular, as partes abaixo qualificadas têm entre si justo e contratado o que segue:</p>

        <h2>Cláusula 1 – Das Partes</h2>
        <h3>1.1 Contratada</h3>
        <p>DATADARK Tecnologia, inscrita no CNPJ nº 67.104.424/0001-77, com sede na Rua Platão, 265 – Jardim Itu Sabará – Porto Alegre/RS, neste ato representada por Julio Marques, Técnico Responsável.</p>

        <h3 style="margin-top:8mm">2 Contratante</h3>
        <div class="line-field"><label for="contratante_nome">Nome/Razão Social:</label><input class="line-input" id="contratante_nome" name="contratante_nome" type="text"></div>
        <div class="line-field"><label for="contratante_doc">CPF/CNPJ:</label><input class="line-input" id="contratante_doc" name="contratante_doc" type="text"></div>
        <div class="line-field"><label for="contratante_endereco">Endereço:</label><input class="line-input" id="contratante_endereco" name="contratante_endereco" type="text"></div>
        <div class="line-field"><label for="contratante_telefone">Telefone:</label><input class="line-input" id="contratante_telefone" name="contratante_telefone" type="tel"></div>
        <div class="line-field"><label for="contratante_email">E-mail:</label><input class="line-input" id="contratante_email" name="contratante_email" type="email"></div>
    </div>

    <table class="company-box">
        <tr>
            <td>
                <div class="company-name">DATADARK TECNOLOGIA</div>
                CNPJ: 67.104.424/0001-77<br>
                Rua Platão, 265<br>
                Jardim Itu Sabará<br>
                Porto Alegre/RS<br>
                CEP: 91210-310
            </td>
            <td>
                (51) 99519-0259<br>
                www.datadark.com.br<br>
                contato@datadark.com.br<br>
                Porto Alegre e Região Metropolitana
            </td>
        </tr>
    </table>
    <div class="footer">www.datadark.com.br &nbsp;•&nbsp; contato@datadark.com.br &nbsp;•&nbsp; (51) 99519-0259 &nbsp; | &nbsp; Página 1 de 4</div>
</section>

<section class="sheet">
    <img class="header-img" src="assets/cabecalho-datadark.png" alt="DATADARK Tecnologia">

    <h2 style="margin-top:0">Cláusula 2 – Do Objeto</h2>
    <p>O presente contrato tem por objeto a prestação de serviços especializados em tecnologia da informação, podendo incluir:</p>
    <div class="two-cols">
        <ul class="service-list">
            <li>Manutenção de computadores;</li>
            <li>Instalação e configuração de sistemas operacionais;</li>
            <li>Suporte remoto e presencial;</li>
            <li>Configuração de redes cabeadas e Wi-Fi;</li>
            <li>Configuração de roteadores e switches;</li>
        </ul>
        <ul class="service-list">
            <li>Implantação e administração de servidores Linux;</li>
            <li>Serviços de backup;</li>
            <li>Recuperação de dados;</li>
            <li>Segurança da informação;</li>
            <li>Consultoria em tecnologia.</li>
        </ul>
    </div>

    <h2>Cláusula 3 – Descrição dos Serviços Contratados</h2>
    <textarea class="services-box" id="descricao_servicos" name="descricao_servicos"></textarea>

    <h2>Cláusula 4 – Prazo de Execução</h2>
    <p>O serviço será executado no prazo acordado entre as partes.</p>
    <table class="date-grid">
        <tr>
            <td>Data prevista de início:<br><input type="date" id="data_inicio" name="data_inicio"></td>
            <td>Data prevista de conclusão:<br><input type="date" id="data_conclusao" name="data_conclusao"></td>
        </tr>
    </table>

    <h2>Cláusula 5 – Valores</h2>
    <table class="value-table">
        <tr>
            <td>Valor dos serviços:</td>
            <td>R$ <input type="text" inputmode="decimal" class="money" id="valor_servicos" name="valor_servicos"></td>
        </tr>
        <tr>
            <td>Valor de equipamentos e materiais:</td>
            <td>R$ <input type="text" inputmode="decimal" class="money" id="valor_materiais" name="valor_materiais"></td>
        </tr>
        <tr>
            <td class="value-total-label">VALOR TOTAL:</td>
            <td class="value-total">R$ <input type="text" id="valor_total" name="valor_total" readonly></td>
        </tr>
    </table>

    <div class="footer">www.datadark.com.br &nbsp;•&nbsp; contato@datadark.com.br &nbsp;•&nbsp; (51) 99519-0259 &nbsp; | &nbsp; Página 2 de 4</div>
</section>

<section class="sheet">
    <img class="header-img" src="assets/cabecalho-datadark.png" alt="DATADARK Tecnologia">

    <h2 style="margin-top:0">Cláusula 6 – Forma de Pagamento</h2>
    <div class="payment-box">
        <label class="payment-item"><input type="checkbox" name="pagamento_pix"> PAGAMENTO POR PIX / CNPJ: 67.104.424/0001-77</label>
        <label class="payment-item"><input type="checkbox" name="pagamento_deposito"> PAGAMENTO POR DEPÓSITO / BANCO: 0260 - Nu Pagamentos S.A - AG: 0001 - CONTA: 590593432-1</label>
        <label class="payment-item"><input type="checkbox" name="pagamento_debito"> PAGAMENTO NO DÉBITO - CARTÃO DE DÉBITO</label>
        <label class="payment-item"><input type="checkbox" name="pagamento_credito"> PAGAMENTO NO CRÉDITO - CARTÃO DE CRÉDITO</label>
        <label class="payment-item"><input type="checkbox" name="pagamento_dinheiro"> PAGAMENTO EM DINHEIRO - R$</label>
        <div class="payment-notes"><label for="pagamento_obs">Observações:</label><input id="pagamento_obs" name="pagamento_obs" type="text"></div>
    </div>

    <h2>Cláusula 7 – Obrigações da Contratada</h2>
    <p>A DATADARK compromete-se a:</p>
    <ul class="service-list">
        <li>Executar os serviços com qualidade técnica;</li>
        <li>Seguir boas práticas de mercado;</li>
        <li>Preservar a confidencialidade das informações;</li>
        <li>Informar limitações ou impedimentos técnicos identificados.</li>
    </ul>

    <h2>Cláusula 8 – Obrigações do Contratante</h2>
    <p>O contratante compromete-se a:</p>
    <ul class="service-list">
        <li>Disponibilizar acesso aos equipamentos;</li>
        <li>Fornecer informações necessárias para execução dos serviços;</li>
        <li>Efetuar os pagamentos conforme acordado;</li>
        <li>Autorizar intervenções necessárias.</li>
    </ul>

    <h2>Cláusula 9 – Backup e Responsabilidade Sobre Dados</h2>
    <p>Sempre que possível, a DATADARK recomendará a realização de backup prévio.</p>
    <p>O contratante declara estar ciente de que intervenções técnicas podem envolver riscos inerentes à manipulação de sistemas e equipamentos.</p>
    <p>Quando não houver contratação específica de serviço de backup, a responsabilidade pela manutenção de cópias de segurança dos dados será do contratante.</p>

    <div class="footer">www.datadark.com.br &nbsp;•&nbsp; contato@datadark.com.br &nbsp;•&nbsp; (51) 99519-0259 &nbsp; | &nbsp; Página 3 de 4</div>
</section>

<section class="sheet">
    <img class="header-img" src="assets/cabecalho-datadark.png" alt="DATADARK Tecnologia">

    <h2 style="margin-top:0">Cláusula 10 – Garantia dos Serviços</h2>
    <div class="guarantee-row">
        <span>Os serviços executados possuem garantia de</span>
        <input class="guarantee-days" id="garantia_dias" name="garantia_dias" type="number" min="0" step="1">
        <span>dias.</span>
    </div>
    <p style="margin-top:7mm"><strong>A garantia não cobre:</strong></p>
    <ul class="guarantee-list">
        <li>Mau uso;</li>
        <li>Vírus ou malware adquiridos posteriormente;</li>
        <li>Danos físicos;</li>
        <li>Alterações realizadas por terceiros.</li>
        <li>Descargas elétricas;</li>
    </ul>

    <h2>Cláusula 11 – Confidencialidade</h2>
    <p>A DATADARK compromete-se a manter sigilo sobre quaisquer informações, documentos ou dados aos quais tenha acesso durante a prestação dos serviços.</p>

    <h2>Cláusula 12 – Rescisão</h2>
    <p>O presente contrato poderá ser rescindido por qualquer das partes mediante comunicação formal.</p>

    <h2>Cláusula 13 – Foro</h2>
    <p>Fica eleito o foro da comarca de <strong>Porto Alegre/RS</strong> para dirimir quaisquer dúvidas oriundas deste contrato.</p>

    <p class="signature-intro">E, por estarem de acordo, as partes assinam o presente contrato.</p>

    <table class="signature-grid">
        <tr>
            <td>
                <div class="signature-title">CONTRATANTE</div>
                <div class="line-field"><label for="assin_nome">Nome:</label><input class="line-input sync-name" id="assin_nome" name="assin_nome" type="text"></div>
                <div class="line-field"><label for="assin_doc">CPF/CNPJ:</label><input class="line-input sync-doc" id="assin_doc" name="assin_doc" type="text"></div>
                <div style="margin-top:8mm">Assinatura:</div>
                <div style="border-bottom:.65pt solid #8f979f; height:9mm"></div>
                <div class="line-field" style="margin-top:3mm"><label for="assin_data">Data:</label><input class="line-input" id="assin_data" name="assin_data" type="date"></div>
            </td>
            <td>
                <div class="signature-title">DATADARK TECNOLOGIA</div>
                <div class="signature-center"><strong>Julio Marques</strong><br><em>Técnico Responsável</em></div>
                <div style="margin-top:9mm">Assinatura:</div>
                <div style="border-bottom:.65pt solid #8f979f; height:9mm"></div>
                <div class="line-field" style="margin-top:3mm"><label for="datadark_data">Data:</label><input class="line-input" id="datadark_data" name="datadark_data" type="date"></div>
            </td>
        </tr>
    </table>

    <div class="footer">www.datadark.com.br &nbsp;•&nbsp; contato@datadark.com.br &nbsp;•&nbsp; (51) 99519-0259 &nbsp; | &nbsp; Página 4 de 4</div>
</section>

</form>

<script>
(function () {
    const nome = document.getElementById('contratante_nome');
    const doc = document.getElementById('contratante_doc');
    const assinNome = document.getElementById('assin_nome');
    const assinDoc = document.getElementById('assin_doc');
    const vServ = document.getElementById('valor_servicos');
    const vMat = document.getElementById('valor_materiais');
    const vTotal = document.getElementById('valor_total');

    function moedaParaNumero(valor) {
        if (!valor) return 0;
        valor = valor.toString().trim().replace(/\s/g, '');
        if (valor.includes(',')) {
            valor = valor.replace(/\./g, '').replace(',', '.');
        }
        return Number(valor.replace(/[^0-9.-]/g, '')) || 0;
    }

    function formatarMoeda(numero) {
        return numero.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function atualizarTotal() {
        vTotal.value = formatarMoeda(moedaParaNumero(vServ.value) + moedaParaNumero(vMat.value));
    }

    nome.addEventListener('input', () => assinNome.value = nome.value);
    doc.addEventListener('input', () => assinDoc.value = doc.value);
    vServ.addEventListener('input', atualizarTotal);
    vMat.addEventListener('input', atualizarTotal);

    window.limparFormulario = function () {
        if (confirm('Deseja realmente limpar todos os campos preenchidos?')) {
            document.getElementById('contratoForm').reset();
            vTotal.value = '';
        }
    };
})();
</script>
</body>
</html>
