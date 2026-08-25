# Leitor-de-Publicao.py

# 🏛️ Portal GGTAB - Extrator e Gerador de Decisões (SEI)

Uma aplicação web desenvolvida em Python e Streamlit para automatizar a leitura, extração de metadados e formatação de processos administrativos e decisões da ANVISA (GGTAB). 

O sistema resolve o gargalo da leitura manual de PDFs do sistema SEI, utilizando Expressões Regulares (RegEx) para identificar penalidades, artigos e autuados. Além disso, gera automaticamente extratos oficiais estruturados e mesclados com o documento original, prontos para publicação.

## 🚀 Principais Funcionalidades

- **Extração Inteligente de Metadados:** Algoritmo RegEx avançado para capturar números de decisão, processos, CNPJ/CPF, penalidades (multas, advertências) e resumos legais.
- **Motor de OCR Integrado (Fallback):** Caso o PDF seja escaneado (sem texto selecionável), o sistema aciona automaticamente o `pytesseract` para converter as imagens em texto e prosseguir com a extração.
- **Conformidade com a LGPD:** Máscara automática de documentos sensíveis (anonimização parcial de CPFs de pessoas físicas) antes da geração do extrato público.
- **Manipulação de PDFs:** Utiliza `PyPDF2` e `fpdf` para criar uma capa de extrato formatada e mesclá-la perfeitamente ao PDF original do processo.
- **Acessibilidade e Histórico:** Interface adaptável com controle de zoom na fonte e retenção de histórico de processos gerados durante a sessão ativa.

## 🛠️ Tecnologias Utilizadas

- **Linguagem & Interface:** Python 3.8+ e Streamlit.
- **Processamento de PDF:** `PyPDF2` (leitura e mesclagem) e `fpdf` (geração da capa oficial).
- **Visão Computacional (OCR):** `pytesseract` e `pdf2image` para extração de texto em documentos digitalizados.
- **Manipulação de Texto:** `re` (Expressões Regulares) para o parser jurídico.

## 📦 Como Instalar e Configurar

1. Clone o repositório:
   ```bash
   git clone [https://github.com/seu-usuario/nome-do-repositorio.git](https://github.com/seu-usuario/nome-do-repositorio.git)
   cd nome-do-repositorio

   Crie e ative um ambiente virtual:
  python -m venv venv
  source venv/bin/activate  # No Linux/Mac
  venv\Scripts\activate     # No

  ⚠️ Dependências de Sistema (Obrigatório para o OCR):
  Para que o fallback de leitura de imagens funcione, instale os seguintes pacotes no seu sistema operacional:
  Tesseract OCR: Guia de Instalação
  Poppler (necessário para o pdf2image): Guia de Instalação
  streamlit run app.py

