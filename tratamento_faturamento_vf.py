import streamlit as st
import pandas as pd
from io import BytesIO

# === FUNÇÕES REUTILIZÁVEIS ===
def limpa_moeda(valor):
    if pd.isnull(valor):
        return 0.0
    return float(str(valor).replace('R$', '').replace('.', '').replace(',', '.'))

def calcular_idade(data_nasc):
    if pd.isnull(data_nasc):
        return None
    return int((pd.to_datetime('today') - data_nasc).days / 365.2425)

def cla_faixa_etaria(idade):
    if pd.isnull(idade):
        return None
    if idade < 18:
        return 'abaixo de 18'
    elif 18 <= idade <= 24:
        return '18 a 24'
    elif 25 <= idade <= 34:
        return '25 a 34'
    elif 35 <= idade <= 44:
        return '35 a 44'
    elif 45 <= idade <= 54:
        return '45 a 54'
    elif 55 <= idade <= 64:
        return '55 a 64'
    elif 65 <= idade <= 74:
        return '65 a 74'
    elif 75 <= idade <= 84:
        return '75 a 84'
    else:
        return 'acima de 85'

def cla_regiao_br(end_uf):
    if pd.isna(end_uf):
        return None
    if end_uf in ['AC','AM','AP','PA','PI','RN','RO','RR','TO']:
        return 'norte'
    elif end_uf in ['AL','BA','CE','MA','PB','PE','SE']:
        return 'nordeste'
    elif end_uf in ['DF','GO','MS','MT']:
        return 'centro-oeste'
    elif end_uf in ['ES','MG','SP','RJ']:
        return 'sudeste'
    else:
        return 'sul'

# Função de tratamento do faturamento
def tratar_faturamento(df):
    df = df.loc[:, [
        'participacao', 'proposta', 'num_proposta', 'data_assinatura_proposta',
        'data_vigencia', 'cpf', 'nome_proponente', 'qualificacao', 'data_nascimento', 'sexo', 
        'estado_civil', 'end_cidade', 'end_uf','ultimo_desconto',
        'ultimo_capital', 'forma_pagamento', 'parcelas_aberto',
        'data_ultimo_pagamento', 'programa_beneficio', 'promotor', 'distribuidor',
        'canal_distribuicao', 'aposentado', 'pensionista','status_participacao']]

    df['data_nascimento'] = pd.to_datetime(df['data_nascimento'], errors='coerce')
    df['data_assinatura_proposta'] = pd.to_datetime(df['data_assinatura_proposta'], errors='coerce')
    df['data_vigencia'] = pd.to_datetime(df['data_vigencia'], errors='coerce')
    df['data_ultimo_pagamento'] = pd.to_datetime(df['data_ultimo_pagamento'], errors='coerce')

    df['idade'] = df['data_nascimento'].apply(calcular_idade)
    df['faixa_etaria'] = df['idade'].apply(cla_faixa_etaria)
    df['regiao_uf'] = df['end_uf'].apply(cla_regiao_br)

    df['programa_beneficio'] = df['programa_beneficio'].replace({
        'VIVERMAIS': 'VIVERMAIS PROTEÇÃO'})

    df['status_participacao'] = df['status_participacao'].str.lower()
    df['status_participacao'] = df['status_participacao'].str.replace('1ª','1a', regex=False)
    df['parcelas_aberto'] = pd.to_numeric(df['parcelas_aberto'], errors='coerce')
    df = df.dropna(subset=['status_participacao'])
    df = df[~df['status_participacao'].str.contains('cancelamento|recusada|pendente', case=False, na=False)]

    def classifica_faturado(status_participacao, parcelas_aberto):
        if pd.isna(status_participacao) or pd.isna(parcelas_aberto):
            return 'inválido'

        status_participacao = str(status_participacao).lower()

        if 'ativo' in status_participacao and '1a' not in status_participacao and 'suspenso' not in status_participacao and parcelas_aberto >= 0:
            return 'pagamento regular'
        elif '1a' in status_participacao and parcelas_aberto == 1:
            return 'pagamento adesão'
        elif '1a' in status_participacao and parcelas_aberto > 1:
            return 'nova tentativa adesão'
        elif 'suspenso' in status_participacao:
            return 'regularização'
        else:
            return 'inválido'

    df['tipo_faturamento'] = df.apply(
        lambda row: classifica_faturado(row['status_participacao'], row['parcelas_aberto']),
        axis=1
    )
    return df

# Interface Streamlit
st.set_page_config(page_title="Tratador de Faturamento", layout="centered")
st.title("🔧 Gerador de Faturamento Instituto - Programa de Benefícios")

# Upload do arquivo
uploaded_file = st.file_uploader("Envie a base para Faturamento (.csv)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, delimiter=';', encoding='latin-1')
    st.write("Prévia dos dados recebidos:", df.head())

    # Processamento
    df_tratado = tratar_faturamento(df)
    st.success("Arquivo tratado com sucesso!")
    st.write("Prévia dos dados tratados:", df_tratado.head())

    # Preparar para download
    buffer = BytesIO()
    df_tratado.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Baixar Arquivo Tratado",
        data=buffer,
        file_name="faturamento_mensal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
