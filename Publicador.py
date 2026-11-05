import streamlit as st
import re
import io
from PyPDF2 import PdfReader, PdfWriter
from fpdf import FPDF

# ==========================================
# 1. MOTOR DE EXTRAÇÃO (CÉREBRO 9.0 ADAPTATIVO)
# ==========================================
def extrair_dados_pdf(arquivo_pdf):
    leitor = PdfReader(arquivo_pdf)
    texto_completo = ""
    for pagina in leitor.pages:
        texto_extraido = pagina.extract_text()
        if texto_extraido: texto_completo += texto_extraido + "\n"
    
    texto_limpo = re.sub(r'\s+', ' ', texto_completo)
    
    dados = {
        "num_decisao": "", "processo": "", "autuado": "", "documento": "Não possui", "auto_infracao": "",
        "penalidade": "", "tipo_decisao": "", "resumo": "", "enquadramento": "", 
        "info_adicional": "", "palavras_chave": "", "data_pub": ""
    }
    
    # 1. Data da Assinatura SEI
    matches_data = re.findall(r"assinado eletronicamente.*?em\s+(\d{2}/\d{2}/\d{4})", texto_limpo, re.IGNORECASE)
    if matches_data: dados["data_pub"] = matches_data[-1] 

    # 2. Número da Decisão, Processo, Autuado, AIS, Expediente
    match_decisao = re.search(r"DECIS[AÃ]O\s*(?:N[º°o]\s*)?([0-9\.\/-]+)", texto_completo, re.IGNORECASE)
    if match_decisao and any(char.isdigit() for char in match_decisao.group(1)): dados["num_decisao"] = match_decisao.group(1).strip()
    
    match_processo = re.search(r"Processo(?:s)?\s*(?:n[º°o\.])?\s*[:\-]?\s*([0-9\.\/-]+)", texto_completo, re.IGNORECASE)
    if match_processo: dados["processo"] = match_processo.group(1).strip()
    
    match_autuado = re.search(r"(?:Autuad[ao]|Empresa|Interessad[ao])\s*[:\-]?\s*([^\n\r]+)", texto_completo, re.IGNORECASE)
    if match_autuado: dados["autuado"] = re.split(r'\s*-\s*CNPJ|\s*CNPJ|\s*CPF|\s*AIS', match_autuado.group(1), flags=re.IGNORECASE)[0].strip()
    
    match_ais = re.search(r"AIS\s*(?:n(?:[º°o]|.)?)?\s*[:\-]?\s*([^\n\r]+)", texto_completo, re.IGNORECASE)
    if match_ais: dados["auto_infracao"] = match_ais.group(1).strip()
    
    match_expediente = re.search(r"Expediente\s*(?:do\s*Recurso)?\s*(?:n(?:[º°o]|.)?)?\s*[:\-]?\s*([^\n\r]+)", texto_completo, re.IGNORECASE)
    if match_expediente: dados["info_adicional"] = f"Expediente do Recurso: {match_expediente.group(1).strip()}"

    # 3. PENALIDADES COMPLEXAS (NOVA LÓGICA)
    bloco_decisao = re.search(r"(?:aplico|condenada(?: ao pagamento)?|aplicada)(.*?)(?:Publique-se|Encaminhem-se|Desse modo)", texto_limpo, re.IGNORECASE)
    
    if bloco_decisao:
        trecho = bloco_decisao.group(1)
        # Prioridade 1: Valor Total Consolidado
        match_total = re.search(r"(multa.*?valor total.*?R\$\s*[\d\.,]+(?:\s*\([^)]+\))?)", texto_limpo, re.IGNORECASE)
        
        if match_total:
            dados["penalidade"] = match_total.group(1).capitalize()
        else:
            # Prioridade 2: Múltiplas Multas e Combinações
            valores_rs = re.findall(r"R\$\s*[\d\.,]+", trecho, re.IGNORECASE)
            tem_advertencia = re.search(r"\badvert[êe]ncia\b", trecho, re.IGNORECASE)
            tem_interdicao = re.search(r"\binterdi[çc][ãa]o\b", trecho, re.IGNORECASE)
            
            if len(valores_rs) > 1:
                texto_penal = f"Múltiplas multas ({' + '.join(valores_rs)})"
                if tem_advertencia: texto_penal += " + Advertência"
                if tem_interdicao: texto_penal += " + Interdição"
                dados["penalidade"] = texto_penal
            elif len(valores_rs) == 1:
                match_unica = re.search(r"(multa.*?R\$\s*[\d\.,]+(?:\s*\([^)]+\))?)", texto_limpo, re.IGNORECASE)
                if match_unica: dados["penalidade"] = match_unica.group(1).capitalize()
                else: dados["penalidade"] = f"Multa no valor de {valores_rs[0]}"
                if tem_advertencia: dados["penalidade"] += " e Advertência"
            else:
                outras = re.search(r"\b(advert[êe]ncia|notifica[çc][ãa]o|arquivamento|interdi[çc][ãa]o|cancelamento)\b", trecho, re.IGNORECASE)
                if outras: dados["penalidade"] = outras.group(1).capitalize()
                
    # Fallback de segurança caso a nova lógica escape algo
    if not dados.get("penalidade"):
        match_multa = re.search(r"(multa.*?R\$\s*[\d\.,]+(?:\s*\([^)]+\))?)", texto_limpo, re.IGNORECASE)
        if match_multa: dados["penalidade"] = match_multa.group(1).capitalize()
        else:
            outras = re.search(r"\b(advert[êe]ncia|notifica[çc][ãa]o|arquivamento|interdi[çc][ãa]o|cancelamento)\b", texto_limpo, re.IGNORECASE)
            if outras: dados["penalidade"] = outras.group(1).capitalize()
            else: dados["penalidade"] = "Não identificada (Revisar manualmente)"

    # 4. CNPJ/CPF com "Não Possui"
    match_doc = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})", texto_completo)
    if match_doc: dados["documento"] = match_doc.group(1).strip()

    # 5. Captura de Tipo de Decisão Multilinha
    linhas = texto_completo.split('\n')
    tipo_decisao_linhas = []
    capturando_tipo = False
    
    for linha in linhas:
        linha_strip = linha.strip()
        if not linha_strip: continue
        if re.match(r"^DECIS[AÃ]O\s*(?:N[º°o]\s*)?[0-9\.\/-]+$", linha_strip, re.IGNORECASE): continue
            
        if not capturando_tipo and re.match(r"^(DECIS[AÃ]O|JULGAMENTO|CANCELAMENTO|NOTIFICA[CÇ][AÃ]O)", linha_strip, re.IGNORECASE):
            capturando_tipo = True
            tipo_decisao_linhas.append(linha_strip)
            continue
            
        if capturando_tipo:
            if re.search(r"^(Processo|Autuad|Empresa|Interessad|AIS|CNPJ|CPF|Expediente)", linha_strip, re.IGNORECASE) or len(tipo_decisao_linhas) >= 4:
                break
            tipo_decisao_linhas.append(linha_strip)

    if tipo_decisao_linhas: dados["tipo_decisao"] = " ".join(tipo_decisao_linhas).upper()
            
    if not dados["tipo_decisao"]:
        if "arquivamento" in dados.get("penalidade", "").lower(): dados["tipo_decisao"] = "DECISÃO DE ARQUIVAMENTO"
        else: dados["tipo_decisao"] = "DECISÃO ADMINISTRATIVA"
            
    # 6. Enquadramento e Resumo
    match_enquadramento = re.search(r"(art(?:igo|\.)\s*\d+.*?Lei.*?\d{4}|Resolu[çc][ãa]o.*?RDC.*?\d{4})", texto_limpo, re.IGNORECASE)
    if match_enquadramento: dados["enquadramento"] = "Infração conforme o " + match_enquadramento.group(1).strip()
    
    match_conclusao = re.search(r"((?:Desse\s*modo|Diante\s*do\s*exposto|Ante\s*o\s*exposto|Isto\s*posto|Pelo\s*exposto|Assim|Considerando).*?(?:proferida|penalidade|arquivamento|provimento|improcedente|procedente|mantida|notificada|advertida|Sanitário)\.)", texto_limpo, re.IGNORECASE)
    if match_conclusao: dados["resumo"] = match_conclusao.group(1).strip()
    else:
        match_decide = re.search(r"(Decid(?:o|e-se).*?\.|Julg(?:o|a-se).*?\.|Fica.*?(?:advertida|notificada).*?\.)", texto_limpo, re.IGNORECASE)
        if match_decide: dados["resumo"] = match_decide.group(1).strip()
            
    # 7. Palavras-chave Dinâmicas
    palavras = [dados["tipo_decisao"].title()] if dados["tipo_decisao"] else []
    if "multa" in dados.get("penalidade", "").lower(): palavras.append("Multa")
    if "advert" in dados.get("penalidade", "").lower(): palavras.append("Advertência")
    if "interdi" in dados.get("penalidade", "").lower(): palavras.append("Interdição")
    if "arquivamento" in dados.get("penalidade", "").lower(): palavras.append("Arquivamento")
    if "NÃO RETRATAÇÃO" in dados.get("tipo_decisao", "").upper(): palavras.append("Recurso Administrativo")
    dados["palavras_chave"] = ", ".join(list(dict.fromkeys(palavras)))

    return dados


# ==========================================
# 2. CONFIGURAÇÃO E INTERFACE
# ==========================================
st.set_page_config(page_title="Gerador GGTAB", layout="wide")
st.markdown("<style>.stApp { background-color: #f4f7f6; }</style>", unsafe_allow_html=True)

AUTOR_COMPLETO = "Agência Nacional de Vigilância Sanitária (ANVISA), Terceira Diretoria (DIRE3), Gerência-Geral de Registro e Fiscalização de Produtos Fumígenos, Derivados ou não do Tabaco (GGTAB)"
CABECALHO_PADRAO = "AGÊNCIA NACIONAL DE VIGILÂNCIA SANITÁRIA\nTERCEIRA DIRETORIA (DIR3)\nGERÊNCIA-GERAL DE REGISTRO E FISCALIZAÇÃO DE PRODUTOS FUMÍGENOS, DERIVADOS OU NÃO DO TABACO (GGTAB)"

def limpar_tudo():
    st.session_state.dados = {
        "num_decisao": "", "local": "Brasília", "data_pub": "", 
        "area": "GGTAB", "tipo_decisao": "", "processo": "", "autuado": "", 
        "documento": "Não possui", "auto_infracao": "", "enquadramento": "", 
        "penalidade": "", "resumo": "", "info_adicional": "", "palavras_chave": ""
    }
    st.session_state.ultimo_arquivo = None
    st.session_state.preview = False 

if "dados" not in st.session_state: limpar_tudo()

st.title("🏛️ Portal de Decisões - GGTAB")
arquivo_pdf = st.file_uploader("Arraste o PDF do Processo SEI", type=["pdf"])

if arquivo_pdf and st.session_state.get("ultimo_arquivo") != arquivo_pdf.name:
    with st.spinner("🤖 A analisar penalidades e extrair dados..."):
        dados_extraidos = extrair_dados_pdf(arquivo_pdf)
        st.session_state.dados.update(dados_extraidos)
        st.session_state.ultimo_arquivo = arquivo_pdf.name
        st.session_state.preview = False

# ==========================================
# 3. FORMULÁRIO DE EDIÇÃO
# ==========================================
st.markdown("### Metadados da Publicação")
c1, c2, c3 = st.columns(3)
with c1: num_decisao = st.text_input("Nº Decisão", value=st.session_state.dados["num_decisao"])
with c2: 
    local = st.selectbox("Local", ["Brasília", "Rio de Janeiro"], index=0 if st.session_state.dados.get("local", "Brasília") == "Brasília" else 1)
with c3: data_pub = st.text_input("Data Publicação (DD/MM/AAAA) *Obrigatório*", value=st.session_state.dados["data_pub"])

st.markdown("### Dados do Processo")
c_area, c_tipo = st.columns(2)
with c_area: area = st.text_input("Área Responsável", value=st.session_state.dados["area"])
with c_tipo: tipo_decisao = st.text_input("Tipo de Decisão", value=st.session_state.dados["tipo_decisao"])

c4, c5 = st.columns(2)
with c4:
    processo = st.text_input("Processo", value=st.session_state.dados["processo"])
    autuado = st.text_input("Autuado", value=st.session_state.dados["autuado"])
    documento = st.text_input("CNPJ ou CPF", value=st.session_state.dados["documento"])
with c5:
    auto_infracao = st.text_input("Auto de Infração nº", value=st.session_state.dados["auto_infracao"])
    penalidade = st.text_input("Penalidade", value=st.session_state.dados["penalidade"])
    palavras_chave = st.text_input("Palavras-chave", value=st.session_state.dados["palavras_chave"])

enquadramento = st.text_area("Enquadramento Legal", value=st.session_state.dados["enquadramento"], height=68)
resumo = st.text_area("Resumo da Decisão", value=st.session_state.dados["resumo"], height=150)
info_adicional = st.text_area("Informações Adicionais", value=st.session_state.dados["info_adicional"], height=68)

st.markdown("---")

# ==========================================
# 4. FLUXO DE PRÉ-VISUALIZAÇÃO E PUBLICAÇÃO
# ==========================================
col_btn1, col_btn2 = st.columns([3, 1])

with col_btn1:
    if st.button("👁️ Gerar Pré-visualização", use_container_width=True):
        st.session_state.preview = True
with col_btn2:
    if st.button("🗑️ Limpar Tudo", use_container_width=True):
        limpar_tudo()
        st.rerun()

if st.session_state.get("preview", False):
    if not arquivo_pdf: st.error("⚠️ Anexe o PDF do processo primeiro.")
    elif not data_pub.strip(): st.error("⚠️ A Data de Publicação é obrigatória.")
    else:
        # Tratamento de LGPD
        doc_str = str(documento).strip()
        if doc_str.lower() == "não possui" or not doc_str:
            doc_f, nome_f = "Não possui", autuado
        else:
            doc_limpo = re.sub(r'[^0-9]', '', doc_str)
            nome_f = "***" if len(doc_limpo) == 11 else autuado
            doc_f = "***.***.***-**" if len(doc_limpo) == 11 else doc_str
        
        titulo_oficial = f"GGTAB-DIRE3-ANVISA - DECISÃO Nº {num_decisao}" if num_decisao else "GGTAB-DIRE3-ANVISA - DECISÃO"
        titulo_busca = f"DECISÃO Nº {num_decisao} - GGTAB/DIRE3/ANVISA" if num_decisao else "DECISÃO - GGTAB/DIRE3/ANVISA"

        # TEXTO FINAL DIDÁTICO COM SEPARADORES
        texto_final = f"""==================================================================
📋 Título: {titulo_oficial}
==================================================================
Nome de Exibição na Busca: {titulo_busca}
Autor: {AUTOR_COMPLETO}
Local e Data (Ano): {local}, {data_pub}
Número do Processo: {processo}
Palavras-chave: {palavras_chave}

==================================================================
📄 EXTRATO DE DECISÃO - {tipo_decisao.upper()}
==================================================================

Processo nº: {processo}
Autuado: {nome_f}
CNPJ/CPF: {doc_f}
Auto de Infração nº: {auto_infracao}
Infração/Enquadramento: {enquadramento}
Penalidade: {penalidade}

Resumo:
{resumo}

Informações adicionais:
{info_adicional if info_adicional else 'Não constam.'}
=================================================================="""

        st.markdown("### 🔍 Pré-visualização da Publicação")
        st.warning("⚠️ **Aviso:** Certifique-se de que os dados abaixo estão corretos. Note que os blocos estão separados para facilitar o seu preenchimento no sistema da Biblioteca.")
        st.text_area("Visão Estruturada:", value=texto_final, height=550, disabled=True)
        
        # Criação do PDF
        texto_pdf_oficial = texto_final.replace("📋 ", "").replace("📄 ", "")
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 7, txt=texto_pdf_oficial.encode('latin-1', 'replace').decode('latin-1'))
        
        pdf_bytes = pdf.output(dest='S')
        pdf_bytes = pdf_bytes.encode('latin-1') if isinstance(pdf_bytes, str) else pdf_bytes
        
        # Mescla com o arquivo original
        writer = PdfWriter()
        reader_capa = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader_capa.pages: writer.add_page(page)
        
        arquivo_pdf.seek(0)
        reader_original = PdfReader(arquivo_pdf)
        for page in reader_original.pages: writer.add_page(page)
        
        pdf_mesclado = io.BytesIO()
        writer.write(pdf_mesclado)
        pdf_mesclado_bytes = pdf_mesclado.getvalue()

        st.markdown("<br>", unsafe_allow_html=True)
        col_pub1, col_pub2 = st.columns(2)
        
        with col_pub1:
            if st.button("🚀 Confirmar e Publicar", type="primary", use_container_width=True):
                st.success("✅ Arquivo publicado! Agora você pode acessa-lo via Biblioteca Digital da Anvisa.")
                st.balloons()
        with col_pub2:
            st.download_button(
                label="📥 Baixar Extrato + Processo Original (PDF Único)",
                data=pdf_mesclado_bytes,
                file_name=f"Publicacao_Completa_GGTAB_{num_decisao}.pdf",
                mime="application/pdf",
                use_container_width=True
            )