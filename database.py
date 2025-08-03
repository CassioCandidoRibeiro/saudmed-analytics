# database.py
# Módulo para interação com o banco de dados Firebird.



######################################################################################



import fdb 
import pandas as pd
import streamlit as st
import numpy as np
from datetime import date, datetime, time
from typing import List, Tuple, Optional, Any, Dict, Union

# Módulos locais
import constants as C
import utils



######################################################################################



# --- Gestão da Conexão ---

@st.cache_resource(ttl=3600, show_spinner="Conectando ao banco de dados...") # Cache por 1 hora
def get_db_connection() -> Optional[fdb.Connection]:
    """
    Estabelece e retorna uma conexão com o banco de dados Firebird usando st.secrets.
    A conexão é cacheada usando st.cache_resource para reutilização.
    Returns:
        Um objeto de conexão fdb.Connection se bem-sucedido, None caso contrário.
        Exibe mensagens de erro no Streamlit em caso de falha.
    """
    try:
        # Verifica se as credenciais estão configuradas em st.secrets
        if "db_credentials" not in st.secrets:
            st.error("Credenciais do banco de dados ('db_credentials') não encontradas em st.secrets.")
            return None
        creds: Dict[str, Any] = st.secrets["db_credentials"]
        required_keys: List[str] = ["host", "port", "database", "user", "password"]
        # Valida se as chaves essenciais existem
        missing_keys = [key for key in required_keys if key not in creds]
        if missing_keys:
            st.error(f"Credenciais incompletas em st.secrets. Faltando: {missing_keys}")
            return None
        # Tenta converter a porta para inteiro
        try:
            port = int(creds.get("port", 3055)) # Usa 3055 como padrão
        except ValueError:
            st.error(f"Valor inválido para 'port' nas credenciais: '{creds.get('port')}'. Deve ser um número.")
            return None
        # Estabelece a conexão
        con = fdb.connect(
            host=creds.get("host"),
            port=port,
            database=creds.get("database"),
            user=creds.get("user"),
            password=creds.get("password"),
            charset=creds.get("charset", "UTF8") # Usa UTF8 como padrão
        )
        # st.toast("Conexão com banco estabelecida.", icon="🔥") # Feedback opcional
        return con
    except fdb.Error as fb_err:
        # Erro específico do Firebird/fdb
        st.error(f"{C.TEXTO_ERRO_CONEXAO_BD}: Erro FDB - {fb_err}")
        # st.exception(fb_err) # Descomentar para traceback completo
        return None
    except Exception as e:
        # Outros erros inesperados durante a conexão
        st.error(f"{C.TEXTO_ERRO_CONEXAO_BD}: Erro inesperado - {e}")
        st.exception(e) # Descomentar para traceback completo
        return None



######################################################################################



# --- Funções de Carregamento de Dados ---

def _execute_query(query: str, params: Optional[Tuple[Any, ...]] = None) -> pd.DataFrame:
    """
    Executa uma query SQL parametrizada de forma segura e retorna um DataFrame.
    Obtém a conexão do cache, executa a query e realiza um tratamento básico
    de tipos de dados (decodificação de bytes).
    Args:
        query: A string da query SQL com placeholders (?).
        params: Uma tupla de parâmetros para substituir os placeholders.
    Returns:
        Um DataFrame Pandas com os resultados da query, ou um DataFrame vazio
        em caso de erro de conexão ou execução.
    """
    con = get_db_connection()
    if con is None:
        # Mensagem de erro já foi exibida por get_db_connection
        return pd.DataFrame() # Retorna DF vazio
    try:
        # Executa a query usando parâmetros seguros
        # A UserWarning sobre DBAPI2 pode ser ignorada se a leitura funcionar
        df = pd.read_sql(query, con, params=params)
        # --- Tratamento Pós-Leitura Otimizado ---
        # 1. Decodificar colunas de bytes (BLOBs)
        charset = st.secrets.get("db_credentials", {}).get("charset", "UTF8")
        for col in df.select_dtypes(include=['object']).columns:
            # Verifica se a coluna contém bytes (checa o primeiro valor não nulo)
            first_valid = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(first_valid, bytes):
                try:
                    # Aplica decodificação, ignorando erros
                    df[col] = df[col].apply(lambda x: x.decode(charset, errors='ignore') if isinstance(x, bytes) else x)
                except Exception as decode_err:
                    st.warning(f"Erro ao decodificar coluna '{col}' com charset '{charset}': {decode_err}. Tentando como string.")
                    # Se a decodificação falhar, trata como string na próxima etapa
        # 2. Converter outras colunas 'object' para string, tratando None/NaN
        # Isso evita erros em operações .str futuras e lida com possíveis Nones
        for col in df.select_dtypes(include=['object']).columns:
            # Se ainda for object (não era bytes ou falhou decode) ou contém nulos
            if df[col].dtype == 'object' or df[col].isnull().any():
                df[col] = df[col].fillna('').astype(str) # Preenche NaN com '' e converte
        return df
    except fdb.Error as fb_err:
        st.error(C.TEXTO_ERRO_CARREGAR_DADOS.format(e=f"Erro FDB: {fb_err}"))
        # st.exception(fb_err) # Descomentar para debug
        return pd.DataFrame()
    except Exception as e:
        st.error(C.TEXTO_ERRO_CARREGAR_DADOS.format(e=f"Erro inesperado: {e}"))
        st.exception(e) # Descomentar para debug
        return pd.DataFrame()
    # Nota: A conexão é gerenciada pelo cache_resource, não precisa fechar aqui.



######################################################################################



# --- Funções Específicas por Aba/Seção 
@st.cache_data(ttl=600, show_spinner="Carregando marcas...")
def load_marcas() -> List[str]:
    """Carrega a lista de marcas distintas de mercadorias ativas."""
    query = f"SELECT DISTINCT MARCA FROM MERCADORIAS WHERE ATIVO = ? AND MARCA IS NOT NULL ORDER BY MARCA"
    params = (C.MERCADORIA_ATIVA,)
    df = _execute_query(query, params)
    return df['MARCA'].tolist() if not df.empty and 'MARCA' in df.columns else []



######################################################################################



# -- Filtro de Categorias
@st.cache_data(ttl=600, show_spinner="Carregando categorias...")
def load_categorias() -> List[str]:
    """Carrega a lista de categorias (grupos de produtos) distintas."""
    query = f"SELECT DISTINCT GRUPO FROM PRODGRUPOS ORDER BY GRUPO"
    df = _execute_query(query)
    return df['GRUPO'].tolist() if not df.empty and 'GRUPO' in df.columns else []



######################################################################################


# -- Consulta relatório de compras apenas Brasil
@st.cache_data(ttl=600, show_spinner="Carregando dados Compras BR...")
def load_compras_brasil_data(
    data_inicio: date,
    data_fim_query: datetime, # Já ajustada para incluir o dia final
    marca: Optional[str],
    produto: Optional[str],
    categoria: Optional[str]
    ) -> pd.DataFrame:
    """
    Carrega e processa dados para a aba Compras > Brasil.
    Calcula recomendação de compra com base nas vendas do período e estoque atual.
    """
    # Placeholders dinâmicos para a cláusula IN
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    query_base = f'''
        SELECT
            M.MARCA AS "{C.COL_MARCA}",
            PG.GRUPO AS "{C.COL_CATEGORIA}",
            M.CODEMP AS "{C.COL_CODIGO_BR}",
            M.CODORIG AS "{C.COL_CODIGO_PY}",
            M.MERCADORIA AS "{C.COL_PRODUTO}",
            M.CUSTO AS "{C.COL_CUSTO_ORIGINAL}", -- Custo SaudMed
            M.FORNECEDOR AS "{C.COL_FORNECEDOR}", -- Último Fornecedor
            CAST(M.DATA_ULTIMA_ENTRADA AS DATE) AS "{C.COL_ULTIMA_ENTRADA}", -- Data da última Entrada 
            SUM(VP.QUANTIDADE) AS "{C.COL_PRODUTOS_VENDIDOS}",
            M.UNIDADEDESC AS "{C.COL_UNIDADE}",
            COUNT(DISTINCT V."CODIGO") AS "{C.COL_QTD_VENDAS}", -- Contagem de vendas únicas
            ME.SALDO_ESTOQUE AS "{C.COL_ESTOQUE_BR}" -- Saldo atual
        FROM VENDASPRODUTOS VP
        JOIN VENDAS V ON V."CODIGO" = VP.VENDA
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        JOIN PRODGRUPOS PG ON PG."CODIGO" = M.CODIGO_GRUPO
        JOIN MERCADORIAS_ESTOQUE ME ON ME.CODIGO_MERCADORIA = M."CODIGO"
        WHERE M.ATIVO = ?
            AND V.CANCELADA = 'N'
            AND ME.CODIGO_FILIAL = ?
            AND VP.CFOP IN ({cfop_placeholders})
            AND VP.NATUREZA_OPERACAO = ?
            AND V.STATUS = ?
            AND VP.MODO = ?
            AND VP.DATA >= ? -- Data início inclusiva
            AND VP.DATA < ?  -- Data fim exclusiva (usa datetime)
    '''
    params_base: List[Any] = [
        C.MERCADORIA_ATIVA, C.CODIGO_FILIAL_LOJA, *C.CFOP_VENDAS_ESTADUAIS,
        C.NATUREZA_OPERACAO_VENDA, C.STATUS_VENDA_EFETIVADA,
        C.MODO_VENDA_CONCLUIDA, data_inicio, data_fim_query # data_fim_query é datetime
        ]
    # Aplica filtros comuns (Marca, Produto, Categoria)
    query, params = utils.aplicar_filtros_comuns_sql(query_base, params_base, marca, produto, categoria)
    # Adiciona GROUP BY e ORDER BY
    query += f'''
        GROUP BY
            M.MARCA, PG.GRUPO, M.CODEMP, M.CODORIG, M.MERCADORIA,
            M.CUSTO, M.FORNECEDOR, M.DATA_ULTIMA_ENTRADA, M.UNIDADEDESC, ME.SALDO_ESTOQUE
        ORDER BY
            "{C.COL_MARCA}", "{C.COL_PRODUTO}"
            '''
    df = _execute_query(query, tuple(params))
    if df.empty: return pd.DataFrame() # Retorna DF vazio se a query falhar ou não retornar dados
    # --- Cálculos Pós-Consulta no Pandas ---
    try:
        # Converte colunas numéricas essenciais, tratando erros e NaNs
        df[C.COL_CUSTO_ORIGINAL] = pd.to_numeric(df[C.COL_CUSTO_ORIGINAL], errors='coerce').fillna(0.0)
        df[C.COL_PRODUTOS_VENDIDOS] = pd.to_numeric(df[C.COL_PRODUTOS_VENDIDOS], errors='coerce').fillna(0.0)
        df[C.COL_ESTOQUE_BR] = pd.to_numeric(df[C.COL_ESTOQUE_BR], errors='coerce').fillna(0.0)
        df[C.COL_QTD_VENDAS] = pd.to_numeric(df[C.COL_QTD_VENDAS], errors='coerce').fillna(0).astype(int)
        # Calcula custo unitário (revertendo imposto)
        df[C.COL_CUSTO_UNITARIO] = df[C.COL_CUSTO_ORIGINAL].apply(utils.calcular_custo_reverso)
        # Calcula recomendação
        df[C.COL_RECOMENDACAO_BR] = df.apply(
            lambda row: utils.calcular_recomendacao(row[C.COL_PRODUTOS_VENDIDOS], row[C.COL_ESTOQUE_BR]), axis=1
            )
        # Calcula custo previsto da recomendação
        df[C.COL_CUSTO_PREVISTO] = df[C.COL_RECOMENDACAO_BR] * df[C.COL_CUSTO_UNITARIO]
        # Cria texto formatado para recomendação (apenas se > 0)
        df[C.COL_UNIDADE] = df[C.COL_UNIDADE].astype(str).fillna('') # Garante string
        df[C.COL_UNIDADE] = df[C.COL_UNIDADE].str.strip()
        df[C.COL_TEXTO] = df.apply(
            lambda row: f"{row[C.COL_RECOMENDACAO_BR]} {row[C.COL_UNIDADE]} - {row[C.COL_PRODUTO]}" if row[C.COL_RECOMENDACAO_BR] > 0 else "", axis=1
            )
        # Filtra apenas recomendações positivas APÓS todos os cálculos
        df_final = df[df[C.COL_RECOMENDACAO_BR] > 0].reset_index(drop=True)
        # Seleciona e reordena colunas finais para exibição
        colunas_finais = [
            C.COL_MARCA, C.COL_CATEGORIA, C.COL_CODIGO_BR, C.COL_CODIGO_PY, C.COL_PRODUTO,
            C.COL_CUSTO_UNITARIO, C.COL_FORNECEDOR, C.COL_ULTIMA_ENTRADA, C.COL_PRODUTOS_VENDIDOS, C.COL_UNIDADE, C.COL_QTD_VENDAS,
            C.COL_ESTOQUE_BR, C.COL_RECOMENDACAO_BR, C.COL_CUSTO_PREVISTO, C.COL_TEXTO
            ]
        # Garante que apenas colunas existentes sejam selecionadas
        colunas_existentes = [col for col in colunas_finais if col in df_final.columns]
        return df_final[colunas_existentes].copy()
    except Exception as e:
        st.error(f"Erro ao processar dados de Compras BR pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame() # Retorna DF vazio em caso de erro no processamento



######################################################################################


# Relatório de Compras Geral
@st.cache_data(ttl=600, show_spinner="Carregando catálogo geral...")
def load_catalogo_geral_data(
    marca: Optional[str],
    produto: Optional[str],
    categoria: Optional[str]
    ) -> pd.DataFrame:
    """Carrega dados do catálogo de produtos ativos para a aba Compras > Geral."""
    query_base = f'''
        SELECT
            M.CODEMP AS "{C.COL_CODIGO_BR}",
            M.CODORIG AS "{C.COL_CODIGO_PY}",
            M.MARCA AS "{C.COL_MARCA}",
            M.MERCADORIA AS "{C.COL_PRODUTO}",
            PG.GRUPO AS "{C.COL_CATEGORIA}",
            M.CUSTO AS "{C.COL_CUSTO_ORIGINAL}", -- Custo bruto
            M.FORNECEDOR AS "{C.COL_FORNECEDOR}", -- Último Fornecedor
            CAST(M.DATA_ULTIMA_ENTRADA AS DATE) AS "{C.COL_ULTIMA_ENTRADA}", -- Data da última Entrada
            U.ABREVIATURA AS "{C.COL_UNIDADE}",
            ME.SALDO_ESTOQUE AS "{C.COL_ESTOQUE_BR}"
        FROM MERCADORIAS M
        JOIN PRODGRUPOS PG ON PG."CODIGO" = M.CODIGO_GRUPO
        JOIN MERCADORIAS_ESTOQUE ME ON ME.CODIGO_MERCADORIA = M."CODIGO"
        JOIN UNIDADES U ON U."CODIGO" = M.UNIDADE
        WHERE M.ATIVO = ? AND ME.CODIGO_FILIAL = ?
    '''
    params_base: List[Any] = [C.MERCADORIA_ATIVA, C.CODIGO_FILIAL_LOJA]
    query, params = utils.aplicar_filtros_comuns_sql(query_base, params_base, marca, produto, categoria)
    query += f' ORDER BY "{C.COL_MARCA}", "{C.COL_PRODUTO}"'
    df = _execute_query(query, tuple(params))
    if df.empty: return pd.DataFrame()
    try:
        # Calcula custo unitário (revertendo imposto)
        df[C.COL_CUSTO_ORIGINAL] = pd.to_numeric(df[C.COL_CUSTO_ORIGINAL], errors='coerce').fillna(0.0)
        df[C.COL_CUSTO_UNITARIO] = df[C.COL_CUSTO_ORIGINAL].apply(utils.calcular_custo_reverso)
        # Garante tipos corretos para colunas chave e de exibição
        df[C.COL_CODIGO_PY] = df[C.COL_CODIGO_PY].astype(str).fillna('')
        df[C.COL_ESTOQUE_BR] = pd.to_numeric(df[C.COL_ESTOQUE_BR], errors='coerce').fillna(0).astype(int)
        df[C.COL_UNIDADE] = df[C.COL_UNIDADE].astype(str).fillna('')
        df[C.COL_UNIDADE] = df[C.COL_UNIDADE].str.strip()
        # Seleciona colunas relevantes
        cols_selecionadas = [
            C.COL_CODIGO_BR, C.COL_CODIGO_PY, C.COL_MARCA, C.COL_PRODUTO,
            C.COL_CATEGORIA, C.COL_CUSTO_UNITARIO, C.COL_FORNECEDOR, C.COL_ULTIMA_ENTRADA, C.COL_UNIDADE, C.COL_ESTOQUE_BR
        ]
        cols_existentes = [col for col in cols_selecionadas if col in df.columns]
        return df[cols_existentes].copy()
    except Exception as e:
        st.error(f"Erro ao processar dados do catálogo geral pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame()



######################################################################################


# VENDAS BRASIL GERAL
@st.cache_data(ttl=600, show_spinner="Carregando vendas BR agrupadas...")
def load_vendas_brasil_agrupado_data(
    data_inicio: date,
    data_fim_query: datetime,
    marca: Optional[str],
    produto: Optional[str],
    categoria: Optional[str]
    ) -> pd.DataFrame:
    """Carrega dados de vendas BR agrupadas por produto para a aba Compras > Geral."""
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    query_base = f'''
        SELECT
            VP.CODEMP AS "{C.COL_CODIGO_BR}", -- Chave para merge
            SUM(VP.QUANTIDADE) AS "{C.COL_VENDAS_BR}" -- Vendas agrupadas
        FROM VENDASPRODUTOS VP
            JOIN VENDAS V ON V."CODIGO" = VP.VENDA
            JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
            JOIN PRODGRUPOS PG ON PG."CODIGO" = M.CODIGO_GRUPO
            JOIN MERCADORIAS_ESTOQUE ME ON ME.CODIGO_MERCADORIA = M."CODIGO" -- Join para filtros
        WHERE 1=1 
            and M.ATIVO = ? 
            AND ME.CODIGO_FILIAL = ?
            AND VP.CFOP IN ({cfop_placeholders})
            AND V.CANCELADA = 'N'
            AND VP.NATUREZA_OPERACAO = ? 
            AND V.STATUS = ? 
            AND VP.MODO = ?
            AND VP.DATA >= ? 
            AND VP.DATA < ?
            '''
    params_base: List[Any] = [
        C.MERCADORIA_ATIVA, C.CODIGO_FILIAL_LOJA, *C.CFOP_VENDAS_ESTADUAIS,
        C.NATUREZA_OPERACAO_VENDA, C.STATUS_VENDA_EFETIVADA, 
        C.MODO_VENDA_CONCLUIDA, data_inicio, data_fim_query
        ]
    query, params = utils.aplicar_filtros_comuns_sql(query_base, params_base, marca, produto, categoria)
    query += f' GROUP BY VP.CODEMP' # Agrupa por produto (Cod BR)
    df = _execute_query(query, tuple(params))
    if df.empty: return pd.DataFrame(columns=[C.COL_CODIGO_BR, C.COL_VENDAS_BR]) # Retorna DF vazio com colunas esperadas
    try:
        # Garante tipo inteiro para Vendas BR
        df[C.COL_VENDAS_BR] = pd.to_numeric(df[C.COL_VENDAS_BR], errors='coerce').fillna(0).astype(int)
        # Garante tipo string para Cod BR
        df[C.COL_CODIGO_BR] = df[C.COL_CODIGO_BR].astype(str).fillna('')
        return df[[C.COL_CODIGO_BR, C.COL_VENDAS_BR]].copy() # Seleciona apenas as colunas necessárias
    except Exception as e:
        st.error(f"Erro ao processar vendas BR agrupadas pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame(columns=[C.COL_CODIGO_BR, C.COL_VENDAS_BR])



######################################################################################



# VENDAS BRASIL GERAL - MENOS STANLEY
@st.cache_data(ttl=600, show_spinner="Carregando vendas BR agrupadas...")
def load_vendas_brasil_agrupado_data_menos_stanley(
    data_inicio: date,
    data_fim_query: datetime,
    marca: Optional[str],
    produto: Optional[str],
    categoria: Optional[str]
    ) -> pd.DataFrame:
    """Carrega dados de vendas BR agrupadas por produto para a aba Compras > Geral."""
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    query_base = f'''
        SELECT
            VP.CODEMP AS "{C.COL_CODIGO_BR}", -- Chave para merge
            SUM(VP.QUANTIDADE) AS "{C.COL_VENDAS_BR}" -- Vendas agrupadas
        FROM VENDASPRODUTOS VP
            JOIN VENDAS V ON V."CODIGO" = VP.VENDA
            JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
            JOIN PRODGRUPOS PG ON PG."CODIGO" = M.CODIGO_GRUPO
            JOIN MERCADORIAS_ESTOQUE ME ON ME.CODIGO_MERCADORIA = M."CODIGO" -- Join para filtros
            LEFT JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI -- Join para filtras clientes e filtrar Stanleys 
        WHERE M.ATIVO = ? 
            AND ME.CODIGO_FILIAL = ?
            AND VP.CFOP IN ({cfop_placeholders})
            AND V.CANCELADA = 'N'
            AND VP.NATUREZA_OPERACAO = ? 
            AND V.STATUS = ? 
            AND VP.MODO = ?
            AND VP.DATA >= ? 
            AND VP.DATA < ?
            AND (PE.NOMEFANTASIA NOT LIKE '%STANLEY%HAIR%' OR PE.NOMEFANTASIA IS NULL) -- Filtro para evitar Stanley
            '''
    params_base: List[Any] = [
        C.MERCADORIA_ATIVA, C.CODIGO_FILIAL_LOJA, *C.CFOP_VENDAS_ESTADUAIS,
        C.NATUREZA_OPERACAO_VENDA, C.STATUS_VENDA_EFETIVADA,
        C.MODO_VENDA_CONCLUIDA, data_inicio, data_fim_query
        ]
    query, params = utils.aplicar_filtros_comuns_sql(query_base, params_base, marca, produto, categoria)
    query += f' GROUP BY VP.CODEMP' # Agrupa por produto (Cod BR)
    df = _execute_query(query, tuple(params))
    if df.empty: return pd.DataFrame(columns=[C.COL_CODIGO_BR, C.COL_VENDAS_BR]) # Retorna DF vazio com colunas esperadas
    try:
        # Garante tipo inteiro para Vendas BR
        df[C.COL_VENDAS_BR] = pd.to_numeric(df[C.COL_VENDAS_BR], errors='coerce').fillna(0).astype(int)
        # Garante tipo string para Cod BR
        df[C.COL_CODIGO_BR] = df[C.COL_CODIGO_BR].astype(str).fillna('')
        return df[[C.COL_CODIGO_BR, C.COL_VENDAS_BR]].copy() # Seleciona apenas as colunas necessárias
    except Exception as e:
        st.error(f"Erro ao processar vendas BR agrupadas pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame(columns=[C.COL_CODIGO_BR, C.COL_VENDAS_BR])



######################################################################################



@st.cache_data(ttl=600, show_spinner="Carregando dados de Controlados...")
def load_controlados_data(
    data_inicio: date,
    data_fim_query: datetime,
    marca: Optional[str],
    produto: Optional[str]
    ) -> pd.DataFrame:
    """Carrega e processa dados para a aba Controlados."""
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    query_base = f'''
        SELECT
            -- Extrai primeiro nome do vendedor, tratando ausência de espaço
            SUBSTRING(V.NOMEVEND FROM 1 FOR POSITION(' ' IN V.NOMEVEND || ' ') - 1) AS "{C.COL_VENDEDOR}",
            M.MERCADORIA AS "{C.COL_MERCADORIA_ORIGINAL}", -- Nome bruto do produto
            VP.QUANTIDADE AS "{C.COL_QUANTIDADE_RAW}", -- Quantidade bruta
            M.UNIDADEDESC AS "{C.COL_UNIDADE_DESC}", -- Descrição da unidade
            VP.NUMERO_SERIE_LOTE AS "{C.COL_LOTE}",
            V."CODIGO" AS "{C.COL_VENDA}",
            N.NUMERO_NOTA AS "{C.COL_NFE}",
            V.DATAFATURA AS "{C.COL_DATA}", -- Manter como datetime para formatação posterior
            V.NOME AS "{C.COL_CLIENTE}",
            -- Concatena endereço de forma robusta a nulos
            UPPER(
                COALESCE(PE.RUA, '') ||
                COALESCE(', ' || PE.NUMERO, '') ||
                COALESCE('. ' || PE.BAIRRO, '') ||
                COALESCE('. ' || PE.MUNICIPIO, '') ||
                COALESCE('. ' || PE."UF", '')
            ) AS "{C.COL_ENDERECO}",
            PE.CNPJ AS "{C.COL_CNPJ}",
            PE.CPF AS "{C.COL_CPF}",
            V.DOC AS "{C.COL_DOC}"
        FROM VENDAS V
        JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        LEFT JOIN NFE N ON N.CODIGO_VENDA = V.CODIGO_NFE -- LEFT JOIN para incluir vendas sem NFE associada
        LEFT JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI -- LEFT JOIN caso cliente possa ser nulo
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        LEFT JOIN PRODGRUPOS PG ON PG."CODIGO" = M.CODIGO_GRUPO -- LEFT JOIN para filtro comum de marca/produto
        WHERE V.NATUREZA = ?
            AND V.CANCELADA = 'N'
            AND VP.CFOP IN ({cfop_placeholders})
            AND V.STATUS = ? 
            AND V.VENDA_FATURADA = ? 
            AND VP.MODO = ?
            AND V.DATAFATURA >= ? 
            AND V.DATAFATURA < ?
            AND M.CODIGO_GRUPO = ? -- Filtro específico para grupo de controlados
            '''
    params_base: List[Any] = [
        C.NATUREZA_OPERACAO_VENDA, *C.CFOP_VENDAS_ESTADUAIS,
        C.STATUS_VENDA_EFETIVADA, C.VENDA_FATURADA_SIM,
        C.MODO_VENDA_CONCLUIDA, data_inicio, data_fim_query, C.CODIGO_GRUPO_CONTROLADOS
        ]
    # Aplica filtros comuns (Marca, Produto), Categoria não é necessária (já filtrado por Grupo)
    query, params = utils.aplicar_filtros_comuns_sql(query_base, params_base, marca, produto, None)
    query += f' ORDER BY "{C.COL_DATA}", "{C.COL_MERCADORIA_ORIGINAL}"'
    df = _execute_query(query, tuple(params))
    if df.empty: 
        return pd.DataFrame()
    if 'NFe' in df.columns:
        # Converte para string, remove '.0' de inteiros e substitui NaN por ''
        df['NFe'] = (
            df['NFe']
            .astype(str)
            .str.replace(r'\.0$', '', regex=True)  # Remove .0 de números inteiros
            .replace('nan', '')  # Substitui NaN por string vazia
            )
    try:
        # --- Processamento Pós-Consulta ---
        # Extrai nome do medicamento
        df[C.COL_NOME_MEDICAMENTO] = df[C.COL_MERCADORIA_ORIGINAL].apply(utils.extrair_nome_medicamento)
        # Formata quantidade vendida
        df[C.COL_QUANTIDADE_RAW] = pd.to_numeric(df[C.COL_QUANTIDADE_RAW], errors='coerce').fillna(0).astype(int)
        df[C.COL_UNIDADE_DESC] = df[C.COL_UNIDADE_DESC].astype(str).fillna('') # Garante string
        df[C.COL_QTD_VENDIDA] = df[C.COL_QUANTIDADE_RAW].astype(str) + ' ' + df[C.COL_UNIDADE_DESC]
        # Garante tipos string para colunas de texto que podem ter nulos
        for col in [C.COL_LOTE, C.COL_NFE, C.COL_CNPJ, C.COL_CPF, C.COL_DOC, C.COL_ENDERECO, C.COL_CLIENTE, C.COL_VENDEDOR]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')
        # Seleciona e reordena colunas finais
        colunas_finais = [
            C.COL_DATA, C.COL_VENDEDOR, C.COL_NOME_MEDICAMENTO, C.COL_QTD_VENDIDA, C.COL_LOTE,
            C.COL_VENDA, C.COL_NFE, C.COL_CLIENTE, C.COL_ENDERECO, C.COL_CNPJ, C.COL_CPF, C.COL_DOC
            ]
        cols_existentes = [col for col in colunas_finais if col in df.columns]
        return df[cols_existentes].copy()
    except Exception as e:
        st.error(f"Erro ao processar dados de Controlados pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame()



######################################################################################



@st.cache_data(ttl=600, show_spinner="Carregando vendas Stanley (NF)...")
def load_stanley_vendas_data(
    data_inicio: date,
    data_fim_query: datetime,
    marca: Optional[str],
    produto: Optional[str]
    ) -> pd.DataFrame:
    """Carrega dados das Notas Fiscais emitidas para o cliente Stanley."""
    natureza_placeholders = ",".join(["?"] * len(C.NATUREZAS_OPERACAO_VENDA_REMESSA))
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    query_base = f'''
        SELECT DISTINCT -- Evita duplicatas de NF se múltiplos itens da mesma NF casarem com filtros
            UPPER(PE.MUNICIPIO) AS "{C.COL_CIDADE}",
            PE.NOME AS "{C.COL_UNIDADE_STANLEY}", -- Nome do cliente
            N.INFORMACOES_COMPLEMENTARES AS "{C.COL_INFO_COMPLEMENTARES}", -- Campo para extrair Pedido Compra
            N.NUMERO_NOTA AS "{C.COL_NF}",
            N.VALOR_TOTAL_PROTUDOS AS "{C.COL_VALOR_PRODUTOS}",
            N.VALOR_FRETE AS "{C.COL_FRETE}",
            N.VALOR_TOTAL_NOTA AS "{C.COL_TOTAL_NOTA}",
            ROUND(SUM((M.CUSTO * VP.QUANTIDADE)),2) AS "{C.COL_CUSTO_TOTAL}",
	        ROUND(SUM(VP.V_TOT) - SUM((M.CUSTO * VP.QUANTIDADE)),2) AS "{C.COL_LUCRO}",
            ROUND((SUM(VP.V_TOT) / SUM(M.CUSTO * VP.QUANTIDADE) - 1) * 100, 0) AS "{C.COL_MARGEM}",
            V.TRANSPORTADORA_NOME AS "{C.COL_TRANSPORTADORA}",
            V.DATAFATURA AS "{C.COL_DATA}",
            V.NOMEVEND AS "{C.COL_VENDEDOR}",
            N.CHAVE_ACESSO AS "{C.COL_CHAVE_ACESSO}"
        FROM VENDAS V
        INNER JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        INNER JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        LEFT JOIN NFE N ON N.CODIGO_VENDA = V.CODIGO_NFE
        JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI
        LEFT JOIN PRODGRUPOS PG ON PG."CODIGO" = M.CODIGO_GRUPO -- Para filtro comum de marca/produto
        WHERE 1=1
            AND V.NATUREZA IN ({natureza_placeholders})
            AND V.CANCELADA = 'N'
            AND VP.CFOP IN ({cfop_placeholders})
            AND V.STATUS = ? 
            AND V.VENDA_FATURADA = ? 
            AND VP.MODO = ?
            AND V.DATAFATURA >= ? 
            AND V.DATAFATURA < ?
            AND PE.NOMEFANTASIA LIKE ? -- Filtro específico Stanley
        GROUP BY 
            UPPER(PE.MUNICIPIO),
            PE.NOME,
            N.INFORMACOES_COMPLEMENTARES,
            N.NUMERO_NOTA,
            N.VALOR_TOTAL_PROTUDOS,
            N.VALOR_FRETE,
            N.VALOR_TOTAL_NOTA,
            V.TRANSPORTADORA_NOME,
            V.DATAFATURA,
            V.NOMEVEND,
            N.CHAVE_ACESSO
            '''
    params_base: List[Any] = [
        *C.NATUREZAS_OPERACAO_VENDA_REMESSA, *C.CFOP_VENDAS_ESTADUAIS,
        C.STATUS_VENDA_EFETIVADA, C.VENDA_FATURADA_SIM,
        C.MODO_VENDA_CONCLUIDA, data_inicio, data_fim_query,
        C.FILTRO_NOME_FANTASIA_STANLEY # Parâmetro para LIKE
        ]
    # Aplica filtros comuns (Marca, Produto), Categoria não relevante aqui
    query, params = utils.aplicar_filtros_comuns_sql(query_base, params_base, marca, produto, None)
    query += f' ORDER BY "{C.COL_DATA}" DESC, "{C.COL_NF}" DESC' # Ordena por data e NF mais recentes
    df = _execute_query(query, tuple(params))
    if df.empty: return pd.DataFrame()
    try:
        # --- Pós-processamento ---
        # Extrai pedido de compra
        df[C.COL_PEDIDO_COMPRA] = df[C.COL_INFO_COMPLEMENTARES].apply(utils.extrair_pedido_compra)
        # Renomeia/preenche coluna de observações
        df[C.COL_OBSERVACOES_NOTA] = df[C.COL_INFO_COMPLEMENTARES].astype(str).fillna('')
        # Converte colunas monetárias para numérico (float), tratando possíveis strings com vírgula/ponto
        cols_monetarias = [C.COL_VALOR_PRODUTOS, C.COL_FRETE, C.COL_TOTAL_NOTA]
        for col in cols_monetarias:
            if df[col].dtype == 'object':
                # Remove pontos de milhar e substitui vírgula decimal por ponto ANTES de converter
                df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        # Garante tipos string para outras colunas
        for col in [C.COL_CIDADE, C.COL_UNIDADE_STANLEY, C.COL_NF, C.COL_TRANSPORTADORA, C.COL_VENDEDOR, C.COL_CHAVE_ACESSO]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')
        # Seleciona e reordena colunas finais
        colunas_finais = [
            C.COL_DATA, C.COL_CIDADE, C.COL_UNIDADE_STANLEY, C.COL_PEDIDO_COMPRA, C.COL_NF,
            C.COL_VALOR_PRODUTOS, C.COL_FRETE, C.COL_TOTAL_NOTA, C.COL_CUSTO_TOTAL, C.COL_LUCRO, C.COL_MARGEM, C.COL_TRANSPORTADORA,
            C.COL_VENDEDOR, C.COL_CHAVE_ACESSO, C.COL_OBSERVACOES_NOTA
            ]
        cols_existentes = [col for col in colunas_finais if col in df.columns]
        return df[cols_existentes].copy()
    except Exception as e:
        st.error(f"Erro ao processar dados de Vendas Stanley (NF) pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame()



######################################################################################



@st.cache_data(ttl=600, show_spinner="Carregando produtos vendidos para Stanley...")
def load_stanley_produtos_data(
    data_inicio: date,
    data_fim_query: datetime,
    vendedor: Optional[str],
    produto_filtro: Optional[str],
    unidade: Optional[str], # Filtro pelo nome do cliente/unidade Stanley
    codigo_produto: Optional[str]
    ) -> pd.DataFrame:
    """Carrega dados detalhados de produtos vendidos para Stanley, com filtros específicos."""
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    query_base = f'''
        SELECT
            V.DATAFATURA AS "{C.COL_DATA}",
            V.NOMEVEND AS "{C.COL_VENDEDOR}",
            V."CODIGO" AS "{C.COL_VENDA}",
            N.NUMERO_NOTA AS "{C.COL_NF}",
            V.NOME AS "{C.COL_UNIDADE_STANLEY}", -- Nome do cliente
            N.INFORMACOES_COMPLEMENTARES AS "{C.COL_INFO_COMPLEMENTARES}", -- Para extrair Compra
            M.CODEMP AS "{C.COL_CODIGO}", -- Código do produto
            M.MERCADORIA AS "{C.COL_PRODUTO}",
            VP.QUANTIDADE AS "{C.COL_QUANTIDADE_RAW}",
            M.CUSTO AS "{C.COL_CUSTO_ORIGINAL}",
            VP.V_TOT AS "{C.COL_V_TOT}" -- Valor total do item na venda
        FROM VENDAS V
        JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        LEFT JOIN NFE N ON N.CODIGO_VENDA = V.CODIGO_NFE
        JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        WHERE 1=1
            AND V.CANCELADA = 'N'
            AND V.NATUREZA = ?
            AND VP.CFOP IN ({cfop_placeholders})
            AND V.STATUS = ? 
            AND VP.MODO = ? 
            AND M.ATIVO = ?
            AND PE.NOMEFANTASIA LIKE ? -- Filtro Stanley
            AND V.DATAFATURA >= ? AND V.DATAFATURA < ?
            '''
    params_base: List[Any] = [
        C.NATUREZA_OPERACAO_VENDA, *C.CFOP_VENDAS_ESTADUAIS,
        C.STATUS_VENDA_EFETIVADA, C.MODO_VENDA_CONCLUIDA,
        C.MERCADORIA_ATIVA, C.FILTRO_NOME_FANTASIA_STANLEY, data_inicio, data_fim_query
        ]
    params = list(params_base) # Cria cópia
    query = query_base
    # Aplica filtros específicos desta aba (adiciona cláusulas AND e parâmetros)
    if vendedor: query += " AND V.NOMEVEND LIKE ?"; params.append(f"%{vendedor}%")
    if produto_filtro: query += " AND M.MERCADORIA LIKE ?"; params.append(f"%{produto_filtro}%")
    if unidade: query += " AND V.NOME LIKE ?"; params.append(f"%{unidade}%") # V.NOME é o cliente
    if codigo_produto: query += " AND M.CODEMP = ?"; params.append(codigo_produto) # Busca exata
    query += f' ORDER BY "{C.COL_DATA}" DESC, "{C.COL_PRODUTO}"'
    df = _execute_query(query, tuple(params))
    if df.empty: return pd.DataFrame()
    try:
        # --- Cálculos Pós-Consulta ---
        # Converte colunas numéricas essenciais
        df[C.COL_CUSTO_ORIGINAL] = pd.to_numeric(df[C.COL_CUSTO_ORIGINAL], errors='coerce').fillna(0.0)
        df[C.COL_QUANTIDADE_RAW] = pd.to_numeric(df[C.COL_QUANTIDADE_RAW], errors='coerce').fillna(0.0)
        df[C.COL_V_TOT] = pd.to_numeric(df[C.COL_V_TOT], errors='coerce').fillna(0.0)
        # Renomeia/Define colunas finais de quantidade e custo
        df[C.COL_QUANTIDADE] = df[C.COL_QUANTIDADE_RAW]
        df[C.COL_CUSTO_UNITARIO] = df[C.COL_CUSTO_ORIGINAL] # Custo direto do DB aqui
        # Calcula Preço Unitário, tratando divisão por zero
        df[C.COL_PRECO_UNITARIO] = np.where(
            df[C.COL_QUANTIDADE] != 0,
            round(df[C.COL_V_TOT] / df[C.COL_QUANTIDADE], 2),
            0.0 # Preço unitário é 0 se quantidade for 0
            )
        # Calcula Margem sobre o Custo, tratando divisão por zero e custo zero
        df[C.COL_MARGEM] = np.where(
            df[C.COL_CUSTO_UNITARIO] != 0,
            round(((df[C.COL_PRECO_UNITARIO] / df[C.COL_CUSTO_UNITARIO]) - 1) * 100, 0),
            np.nan # Margem é indefinida (NaN) se custo for zero
            )
        # Define Total Venda (do item) e extrai Compra (Pedido)
        df[C.COL_TOTAL_VENDA] = df[C.COL_V_TOT]
        df[C.COL_COMPRA_STANLEY] = df[C.COL_INFO_COMPLEMENTARES].apply(utils.extrair_pedido_compra)
        # Garante tipos string
        for col in [C.COL_VENDEDOR, C.COL_NF, C.COL_UNIDADE_STANLEY, C.COL_CODIGO, C.COL_PRODUTO]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')
        # Seleciona e reordena colunas finais
        colunas_finais = [
            C.COL_DATA, C.COL_VENDEDOR, C.COL_VENDA, C.COL_NF, C.COL_UNIDADE_STANLEY, C.COL_COMPRA_STANLEY,
            C.COL_CODIGO, C.COL_PRODUTO, C.COL_QUANTIDADE, C.COL_CUSTO_UNITARIO,
            C.COL_PRECO_UNITARIO, C.COL_MARGEM, C.COL_TOTAL_VENDA
            ]
        cols_existentes = [col for col in colunas_finais if col in df.columns]
        df_final = df[cols_existentes].copy()
        # Ajusta tipos para exibição (float permite NaNs na margem)
        df_final[C.COL_MARGEM] = df_final[C.COL_MARGEM].astype(float)
        df_final[C.COL_QUANTIDADE] = df_final[C.COL_QUANTIDADE].astype(float) # Para formato com separador
        return df_final
    except Exception as e:
        st.error(f"Erro ao processar dados de Produtos Stanley pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame()



######################################################################################



@st.cache_data(ttl=600, show_spinner="Carregando faturamento por unidade Stanley...")
def load_stanley_faturamento_por_unidade_data(
    data_inicio: date,
    data_fim_query: datetime # Já ajustada para incluir o dia final
    ) -> pd.DataFrame:
        """
        Carrega dados de faturamento, custo, lucro e margem por unidade Stanley
        com base em filtros de data.
        """
        # Cria placeholders para a cláusula IN de CFOPs
        cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
        query = f'''
            SELECT
                PE.NOME AS "Unidade",
                ROUND(SUM(VP.V_TOT),2) AS "Faturamento em Produtos",
                ROUND(SUM((M.CUSTO * VP.QUANTIDADE)),2) AS "Custo Total",
                ROUND(SUM(VP.V_TOT) - SUM((M.CUSTO * VP.QUANTIDADE)),2) AS "Lucro",
                ROUND((SUM(VP.V_TOT) / NULLIF(SUM(M.CUSTO * VP.QUANTIDADE), 0) - 1) * 100, 0) AS "Margem"
            FROM VENDAS V
                JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
                JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI
                JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
            WHERE 1=1
                AND V.CANCELADA = 'N'
                AND V.NATUREZA = ? -- Usa a constante de natureza de operação de venda
                AND VP.CFOP IN ({cfop_placeholders})
                AND V.STATUS = ?
                AND VP.MODO = ?
                AND M.ATIVO = ?
                AND PE.NOMEFANTASIA LIKE ? -- Filtro específico para Stanley
                AND V.DATAFATURA >= ? -- Data inicial do filtro
                AND V.DATAFATURA < ?  -- Data final do filtro (ajustada para incluir o dia completo)
            GROUP BY PE.NOME
            ORDER BY "Faturamento em Produtos" DESC;
        '''
        # Parâmetros para a query SQL, seguindo a ordem dos placeholders
        params = [
            C.NATUREZA_OPERACAO_VENDA,
            *C.CFOP_VENDAS_ESTADUAIS, # Desempacota a tupla de CFOPs
            C.STATUS_VENDA_EFETIVADA,
            C.MODO_VENDA_CONCLUIDA,
            C.MERCADORIA_ATIVA,
            C.FILTRO_NOME_FANTASIA_STANLEY,
            data_inicio,
            data_fim_query
        ]
        # Executa a query e obtém o DataFrame
        df = _execute_query(query, tuple(params))
        if df.empty:
            return pd.DataFrame()
        # Renomeia as colunas do DataFrame para usar as constantes definidas em constants.py
        # Isso garante consistência no código e facilita a manutenção
        rename_map = {
            "Unidade": C.COL_UNIDADE_STANLEY,
            "Faturamento em Produtos": C.COL_FATURAMENTO_PRODUTOS,
            "Custo Total": C.COL_CUSTO_TOTAL,
            "Lucro": C.COL_LUCRO,
            "Margem": C.COL_MARGEM
        }
        df.rename(columns=rename_map, inplace=True)
        # Garante que os tipos de dados das colunas numéricas estejam corretos
        # 'errors='coerce'' converterá valores inválidos para NaN, e 'fillna(0.0)' os preencherá com zero.
        try:
            df[C.COL_FATURAMENTO_PRODUTOS] = pd.to_numeric(df[C.COL_FATURAMENTO_PRODUTOS], errors='coerce').fillna(0.0)
            df[C.COL_CUSTO_TOTAL] = pd.to_numeric(df[C.COL_CUSTO_TOTAL], errors='coerce').fillna(0.0)
            df[C.COL_LUCRO] = pd.to_numeric(df[C.COL_LUCRO], errors='coerce').fillna(0.0)
            df[C.COL_MARGEM] = pd.to_numeric(df[C.COL_MARGEM], errors='coerce').fillna(0.0)
            # Garante que a coluna de unidade seja string e preenche NaNs com string vazia
            df[C.COL_UNIDADE_STANLEY] = df[C.COL_UNIDADE_STANLEY].astype(str).fillna('')
        except Exception as e:
            st.error(f"Erro ao processar tipos de dados para faturamento por unidade Stanley: {e}")
            return pd.DataFrame()
        return df

######################################################################################



######################################################################################

# ABA ORÇAMENTOS

@st.cache_data(ttl=600, show_spinner="Carregando itens do orçamento...")
def load_orcamento_produtos_data(codigo_orcamento: int) -> pd.DataFrame:
    """Carrega os produtos (itens) de um orçamento específico."""
    # Validação básica do código
    if not isinstance(codigo_orcamento, int) or codigo_orcamento <= 0:
        st.warning("Código de orçamento inválido.")
        return pd.DataFrame()
    query = f'''
        SELECT
            VP.CODEMP AS "{C.COL_CODIGO}",
            M.MERCADORIA AS "{C.COL_PRODUTO}",
            VP.QUANTIDADE AS "{C.COL_QUANTIDADE_RAW}",
            M.CUSTO AS "{C.COL_CUSTO_ORIGINAL}",
            VP.V_TOT AS "{C.COL_V_TOT}" -- Valor total do item
        FROM VENDAS V
        JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        WHERE 1=1
            AND VP.MODO <> ? -- Inclui itens pendentes (C) e concluídos (O), exclui removidos (R)
            AND V."CODIGO" = ?
            '''
    params = (C.MODO_VENDA_NAO_REMOVIDO, codigo_orcamento)
    df = _execute_query(query, params)
    if df.empty: return pd.DataFrame() # Pode não ter itens ou orçamento não existe
    try:
        # --- Cálculos Pós-Consulta ---
        # Converte colunas numéricas
        df[C.COL_CUSTO_ORIGINAL] = pd.to_numeric(df[C.COL_CUSTO_ORIGINAL], errors='coerce').fillna(0.0)
        df[C.COL_QUANTIDADE_RAW] = pd.to_numeric(df[C.COL_QUANTIDADE_RAW], errors='coerce').fillna(0.0)
        df[C.COL_V_TOT] = pd.to_numeric(df[C.COL_V_TOT], errors='coerce').fillna(0.0)
        # Define colunas finais de quantidade e custo
        df[C.COL_QUANTIDADE] = df[C.COL_QUANTIDADE_RAW]
        df[C.COL_CUSTO_UNITARIO] = df[C.COL_CUSTO_ORIGINAL] # Custo direto do DB
        # Calcula Preço Unitário
        df[C.COL_PRECO_UNITARIO] = np.where(
            df[C.COL_QUANTIDADE] != 0,
            round(df[C.COL_V_TOT] / df[C.COL_QUANTIDADE], 2),
            0.0
            )
        # Calcula Custo Total do item
        df[C.COL_CUSTO_TOTAL] = df[C.COL_CUSTO_UNITARIO] * df[C.COL_QUANTIDADE]
        # Define Preço Total do item
        df[C.COL_PRECO_TOTAL] = df[C.COL_V_TOT]
        # Calcula Margem sobre o Custo
        df[C.COL_MARGEM] = np.where(
            df[C.COL_CUSTO_UNITARIO] != 0,
            round(((df[C.COL_PRECO_UNITARIO] / df[C.COL_CUSTO_UNITARIO]) - 1) * 100, 0),
            np.nan # Indefinida se custo é 0
            )
        # Garante tipos string
        for col in [C.COL_CODIGO, C.COL_PRODUTO]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')
        # Seleciona e reordena colunas finais
        colunas_finais = [
            C.COL_CODIGO, C.COL_PRODUTO, C.COL_QUANTIDADE, C.COL_CUSTO_UNITARIO,
            C.COL_PRECO_UNITARIO, C.COL_CUSTO_TOTAL, C.COL_PRECO_TOTAL, C.COL_MARGEM
            ]
        cols_existentes = [col for col in colunas_finais if col in df.columns]
        df_final = df[cols_existentes].copy()
        # Ajusta tipos para exibição
        df_final[C.COL_MARGEM] = df_final[C.COL_MARGEM].astype(float)
        df_final[C.COL_QUANTIDADE] = df_final[C.COL_QUANTIDADE].astype(float)
        return df_final
    except Exception as e:
        st.error(f"Erro ao processar itens do orçamento {codigo_orcamento} pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame()



######################################################################################



@st.cache_data(ttl=600, show_spinner="Carregando totais do orçamento...")
def load_orcamento_totais_data(codigo_orcamento: int) -> Optional[pd.DataFrame]:
    """
    Carrega os totais gerais (valor produtos, desconto, valor final) de um orçamento.
    Args:
        codigo_orcamento: O código do orçamento a ser consultado.
    Returns:
        Um DataFrame com uma linha contendo os totais, ou None se o orçamento não for encontrado.
    """
    if not isinstance(codigo_orcamento, int) or codigo_orcamento <= 0:
        st.warning("Código de orçamento inválido.")
        return None
    query = f'''
        SELECT
            V.VALOR_TOTAL_PRODUTOS AS "{C.COL_VALOR_EM_PRODUTOS}",
            V.VALOR_DESCONTO_GERAL AS "{C.COL_DESCONTO}",
            V.VLRTOTAL AS "{C.COL_VALOR_FINAL}"
        FROM VENDAS V WHERE V."CODIGO" = ?
        '''
    params = (codigo_orcamento,)
    df = _execute_query(query, params)
    # Retorna None se o DataFrame estiver vazio (orçamento não encontrado)
    if df.empty:
        return None
    try:
        # Converte totais para numérico (float), tratando possíveis strings com vírgula/ponto
        cols_totais = [C.COL_VALOR_EM_PRODUTOS, C.COL_DESCONTO, C.COL_VALOR_FINAL]
        for col in cols_totais:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        return df # Retorna o DataFrame com uma linha
    except Exception as e:
        st.error(f"Erro ao processar totais do orçamento {codigo_orcamento} pós-consulta: {e}")
        st.exception(e)
        return None # Retorna None em caso de erro no processamento

#=======================================================================
# COMPARADOR DE ORÇAMENTOS
#=======================================================================
@st.cache_data(ttl=600, show_spinner="Comparando orçamentos...")
def compare_orcamentos(
    codigo_orcamento_inicial: int,
    codigo_orcamento_final: int
) -> pd.DataFrame:
    """
    Compara os produtos e quantidades de dois orçamentos específicos.

    Args:
        codigo_orcamento_inicial: O código do orçamento de referência (inicial).
        codigo_orcamento_final: O código do orçamento a ser comparado (final).

    Returns:
        Um DataFrame Pandas com a comparação dos produtos, quantidades e diferença.
        Retorna um DataFrame vazio se nenhum dado for encontrado ou em caso de erro.
    """
    if not isinstance(codigo_orcamento_inicial, int) or codigo_orcamento_inicial <= 0:
        st.warning("Código de orçamento inicial inválido.")
        return pd.DataFrame()
    if not isinstance(codigo_orcamento_final, int) or codigo_orcamento_final <= 0:
        st.warning("Código de orçamento final inválido.")
        return pd.DataFrame()

    query = f"""
    WITH produtos_venda AS (
        SELECT
            VP.VENDA AS codigo_venda,
            VP.CODEMP AS codigo_produto,
            M.MERCADORIA AS produto,
            SUM(VP.QUANTIDADE) AS quantidade
        FROM VENDASPRODUTOS VP
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        WHERE 1=1
            AND VP.MODO <> 'R'
            AND VP.VENDA IN (?, ?) -- (INICIAL , FINAL)
        GROUP BY VP.VENDA, VP.CODEMP, M.MERCADORIA
    )
    SELECT
        COALESCE(A.codigo_produto, B.codigo_produto) AS "{C.COL_CODIGO_BR}",
        COALESCE(A.produto, B.produto) AS "{C.COL_PRODUTO}",
        COALESCE(A.quantidade, 0) AS "Inicial",
        COALESCE(B.quantidade, 0) AS "Final",
        COALESCE(A.quantidade, 0) - COALESCE(B.quantidade, 0) AS "{C.COL_DIFERENCA}"
    FROM
        (SELECT * FROM produtos_venda WHERE codigo_venda = ?) A -- INICIAL
    FULL JOIN
        (SELECT * FROM produtos_venda WHERE codigo_venda = ?) B -- FINAL
        ON A.codigo_produto = B.codigo_produto
    ORDER BY "{C.COL_PRODUTO}";
    """
    params = (codigo_orcamento_inicial, codigo_orcamento_final, codigo_orcamento_inicial, codigo_orcamento_final)

    try:
        df = _execute_query(query, params)

        if df.empty:
            st.info("Nenhum registro encontrado para os códigos de orçamento fornecidos.")
            return pd.DataFrame()

        # Garantir tipos de dados corretos (assumindo quantidades como inteiros)
        for col in ["Original", "Final", C.COL_DIFERENCA]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        return df

    except Exception as e:
        st.error(f"Erro ao comparar orçamentos: {e}")
        return pd.DataFrame()






######################################################################################


# ABA LIGEIRINHO

@st.cache_data(ttl=600, show_spinner="Carregando dados de Moto Frete Terceirizado...")
def load_ligeirinho_frete_data(
    data_inicio: date,
    data_fim_query: datetime
    ) -> pd.DataFrame:
    """Carrega dados de frete registrados via campo personalizado."""
    query = f'''
        SELECT
            V.DATAFATURA AS "{C.COL_DATA_HORA}",
            V."CODIGO" AS "{C.COL_VENDA}",
            V.NOMEVEND AS "{C.COL_VENDEDOR}",
            V.VALOR_TOTAL_PRODUTOS AS "{C.COL_VALOR_PRODUTOS}", -- Valor bruto dos produtos na venda
            V.TRANSPORTADORA_NOME AS "{C.COL_TRANSPORTADORA}",
            CPV.VALOR AS "{C.COL_VALOR_FRETE}", -- Valor do frete do campo personalizado
            V.NOME AS "{C.COL_CLIENTE}"
        FROM CAMPOS_PERSONALIZADOS_VALORES CPV
        JOIN VENDAS V ON CPV.CODIGO_TABELA = V."CODIGO"
        WHERE 1=1
            AND V.CANCELADA = 'N'
            AND CPV.CODIGO_CAMPOS_PERSONALIZADOS = ? -- Código Fixo do Frete
            AND V.NATUREZA = ? 
            AND V.STATUS = ? 
            AND V.VENDA_FATURADA = ? 
            AND V.DATAFATURA >= ? 
            AND V.DATAFATURA < ?
        ORDER BY V.DATAFATURA DESC
        '''
    params = (
        C.CODIGO_CAMPO_PERSONALIZADO_FRETE, C.NATUREZA_OPERACAO_VENDA,
        C.STATUS_VENDA_EFETIVADA, C.VENDA_FATURADA_SIM,
        data_inicio, data_fim_query
        )
    df = _execute_query(query, params)
    if df.empty: return pd.DataFrame()
    try:
        # --- Conversão Numérica e Filtro ---
        # Converte Valor Produtos e Valor Frete para numérico
        df[C.COL_VALOR_PRODUTOS] = pd.to_numeric(df[C.COL_VALOR_PRODUTOS], errors='coerce').fillna(0.0)
        # Trata possível formato string com vírgula/ponto no valor do frete
        if df[C.COL_VALOR_FRETE].dtype == 'object':
            df[C.COL_VALOR_FRETE] = df[C.COL_VALOR_FRETE].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df[C.COL_VALOR_FRETE] = pd.to_numeric(df[C.COL_VALOR_FRETE], errors='coerce').fillna(0.0)
        # Filtra apenas registros onde o frete é positivo APÓS conversão
        df_final = df[df[C.COL_VALOR_FRETE] > 0].copy()
        if df_final.empty: return pd.DataFrame() # Retorna vazio se nenhum frete > 0
        # Garante tipos string
        for col in [C.COL_VENDEDOR, C.COL_TRANSPORTADORA, C.COL_CLIENTE]:
            if col in df_final.columns:
                df_final[col] = df_final[col].astype(str).fillna('')
        # Seleciona e reordena colunas finais
        colunas_finais = [
            C.COL_DATA_HORA, C.COL_VENDA, C.COL_VENDEDOR, C.COL_VALOR_PRODUTOS,
            C.COL_TRANSPORTADORA, C.COL_VALOR_FRETE, C.COL_CLIENTE
            ]
        cols_existentes = [col for col in colunas_finais if col in df_final.columns]
        return df_final[cols_existentes]
    except Exception as e:
        st.error(f"Erro ao processar dados de Frete (Ligeirinho) pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame()



######################################################################################



@st.cache_data(ttl=600, show_spinner="Carregando detalhes de vendas por produto...")
def load_produtos_vendas_data(
    data_inicio: date,
    data_fim_query: datetime,
    codigo_venda: Optional[int],
    vendedor: Optional[str],
    cliente: Optional[str],
    codigo_produto: Optional[str],
    marca: Optional[str],
    produto_filtro: Optional[str] # Filtro global de nome do produto
    ) -> pd.DataFrame:
    """Carrega dados detalhados de vendas de produtos para a aba Produtos > Vendas."""
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    query_base = f'''
        SELECT
            V.DATAFATURA AS "{C.COL_DATA}",
            V.NOMEVEND AS "{C.COL_VENDEDOR}",
            V."CODIGO" AS "{C.COL_VENDA}",
            PE.NOME AS "{C.COL_CLIENTE}",
            M.CODEMP AS "{C.COL_CODIGO}", -- Código do produto
            M.MERCADORIA AS "{C.COL_PRODUTO}",
            M.MARCA AS "{C.COL_MARCA}",
            VP.QUANTIDADE AS "{C.COL_QUANTIDADE_RAW}",
            M.CUSTO AS "{C.COL_CUSTO_ORIGINAL}",
            VP.V_TOT AS "{C.COL_V_TOT}" -- Valor total do item
        FROM VENDAS V
        JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        LEFT JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        LEFT JOIN PRODGRUPOS PG ON PG."CODIGO" = M.CODIGO_GRUPO -- Para filtro de marca/produto/categoria
        WHERE 1=1
            AND V.CANCELADA = 'N'
            AND V.NATUREZA = ?
            AND VP.CFOP IN ({cfop_placeholders})
            AND V.STATUS = ? 
            AND V.VENDA_FATURADA = ? 
            AND VP.MODO = ? 
            AND M.ATIVO = ?
            AND V.DATAFATURA >= ? 
            AND V.DATAFATURA < ?
            '''
    params_base: List[Any] = [
        C.NATUREZA_OPERACAO_VENDA, *C.CFOP_VENDAS_ESTADUAIS,
        C.STATUS_VENDA_EFETIVADA, C.VENDA_FATURADA_SIM,
        C.MODO_VENDA_CONCLUIDA, C.MERCADORIA_ATIVA, data_inicio, data_fim_query
        ]
    params = list(params_base) # Copia
    query = query_base
    # Aplica filtros específicos da aba e globais
    if codigo_venda and codigo_venda > 0: query += f' AND V."CODIGO" = ?'; params.append(codigo_venda)
    if vendedor: query += " AND V.NOMEVEND LIKE ?"; params.append(f"%{vendedor}%")
    if cliente: query += " AND PE.NOME LIKE ?"; params.append(f"%{cliente}%")
    if codigo_produto: query += " AND M.CODEMP = ?"; params.append(codigo_produto)
    # Filtros comuns (globais da sidebar) - Categoria não é usada aqui
    if marca and marca != "Todas": query += " AND M.MARCA = ?"; params.append(marca)
    if produto_filtro: query += " AND M.MERCADORIA LIKE ?"; params.append(f"%{produto_filtro}%")
    query += f' ORDER BY "{C.COL_DATA}" DESC, V.NOMEVEND, V."CODIGO", M.MERCADORIA'
    df = _execute_query(query, tuple(params))
    if df.empty: return pd.DataFrame()
    try:
        # --- Cálculos Pós-Consulta ---
        # Conversões numéricas
        df[C.COL_CUSTO_ORIGINAL] = pd.to_numeric(df[C.COL_CUSTO_ORIGINAL], errors='coerce').fillna(0.0)
        df[C.COL_QUANTIDADE_RAW] = pd.to_numeric(df[C.COL_QUANTIDADE_RAW], errors='coerce').fillna(0.0)
        df[C.COL_V_TOT] = pd.to_numeric(df[C.COL_V_TOT], errors='coerce').fillna(0.0)
        # Define colunas finais
        df[C.COL_QUANTIDADE] = df[C.COL_QUANTIDADE_RAW]
        df[C.COL_CUSTO_UNITARIO] = df[C.COL_CUSTO_ORIGINAL] # Custo direto do DB
        df[C.COL_PRECO_TOTAL] = df[C.COL_V_TOT] # Preço total do item
        # Calcula Preço Unitário
        df[C.COL_PRECO_UNITARIO] = np.where(
            df[C.COL_QUANTIDADE] != 0,
            round(df[C.COL_PRECO_TOTAL] / df[C.COL_QUANTIDADE], 2),
            0.0
            )
        # Calcula Margem sobre o Custo
        df[C.COL_MARGEM] = np.where(
            df[C.COL_CUSTO_UNITARIO] != 0,
            round(((df[C.COL_PRECO_UNITARIO] / df[C.COL_CUSTO_UNITARIO]) - 1) * 100, 0),
            np.nan
            )
        # Garante tipos string
        for col in [C.COL_VENDEDOR, C.COL_CLIENTE, C.COL_CODIGO, C.COL_PRODUTO, C.COL_MARCA]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')
        # Seleciona e reordena colunas finais
        colunas_finais = [
            C.COL_DATA, C.COL_VENDEDOR, C.COL_VENDA, C.COL_CLIENTE, C.COL_CODIGO,
            C.COL_PRODUTO, C.COL_MARCA, C.COL_QUANTIDADE, C.COL_CUSTO_UNITARIO,
            C.COL_PRECO_UNITARIO, C.COL_MARGEM, C.COL_PRECO_TOTAL
            ]
        cols_existentes = [col for col in colunas_finais if col in df.columns]
        df_final = df[cols_existentes].copy()
        # Ajusta tipos para exibição
        df_final[C.COL_MARGEM] = df_final[C.COL_MARGEM].astype(float)
        df_final[C.COL_QUANTIDADE] = df_final[C.COL_QUANTIDADE].astype(float)
        return df_final
    except Exception as e:
        st.error(f"Erro ao processar detalhes de vendas por produto pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame()



######################################################################################



@st.cache_data(ttl=600, show_spinner="Carregando dados de Custo x Estoque...")
def load_produtos_custo_estoque_data(
    marca: Optional[str],
    produto: Optional[str],
    categoria: Optional[str]
    ) -> pd.DataFrame:
    """Carrega dados de custo x estoque para produtos ativos com saldo > 0."""
    query_base = f'''
        SELECT
            M.CODEMP AS "{C.COL_CODIGO}",
            M.MERCADORIA AS "{C.COL_PRODUTO}",
            M.CUSTO AS "{C.COL_CUSTO_ORIGINAL}", -- Custo direto do DB
            ME.SALDO_ESTOQUE AS "{C.COL_ESTOQUE}" -- Saldo atual
        FROM MERCADORIAS M
        JOIN MERCADORIAS_ESTOQUE ME ON ME.CODIGO_MERCADORIA = M."CODIGO"
        JOIN PRODGRUPOS PG ON PG."CODIGO" = M.CODIGO_GRUPO
        WHERE M.ATIVO = ? AND ME.CODIGO_FILIAL = ? AND ME.SALDO_ESTOQUE > 0
        '''
    params_base: List[Any] = [C.MERCADORIA_ATIVA, C.CODIGO_FILIAL_LOJA]
    query, params = utils.aplicar_filtros_comuns_sql(query_base, params_base, marca, produto, categoria)
    # A ordenação será feita no Pandas pelo Custo Total
    df = _execute_query(query, tuple(params))
    if df.empty: return pd.DataFrame()
    try:
        # --- Cálculos Pós-Consulta ---
        # Converte tipos numéricos
        df[C.COL_CUSTO_ORIGINAL] = pd.to_numeric(df[C.COL_CUSTO_ORIGINAL], errors='coerce').fillna(0.0)
        df[C.COL_ESTOQUE] = pd.to_numeric(df[C.COL_ESTOQUE], errors='coerce').fillna(0).astype(int) # Estoque como inteiro
        # Define Custo Unitário (usando o custo original aqui)
        df[C.COL_CUSTO_UNITARIO] = df[C.COL_CUSTO_ORIGINAL]
        # Calcula Custo Total
        df[C.COL_CUSTO_TOTAL] = df[C.COL_CUSTO_UNITARIO] * df[C.COL_ESTOQUE]
        # Ordena pelo Custo Total DESCENDENTE
        df_final = df.sort_values(by=C.COL_CUSTO_TOTAL, ascending=False).reset_index(drop=True)
        # Garante tipos string
        for col in [C.COL_CODIGO, C.COL_PRODUTO]:
            if col in df_final.columns:
                df_final[col] = df_final[col].astype(str).fillna('')
        # Seleciona e reordena colunas finais
        colunas_finais = [
            C.COL_CODIGO, C.COL_PRODUTO, C.COL_CUSTO_UNITARIO, C.COL_ESTOQUE, C.COL_CUSTO_TOTAL
            ]
        cols_existentes = [col for col in colunas_finais if col in df_final.columns]
        df_final = df_final[cols_existentes]
        # Ajusta tipo de estoque para float para permitir formatação com separador na UI
        df_final[C.COL_ESTOQUE] = df_final[C.COL_ESTOQUE].astype(float)
        return df_final
    except Exception as e:
        st.error(f"Erro ao processar dados de Custo x Estoque pós-consulta: {e}")
        st.exception(e)
        return pd.DataFrame()



######################################################################################



# aba Produtos > Entradas
@st.cache_data(ttl=600, show_spinner="Carregando dados de Entradas de Produtos...")
def load_entradas_data(
    data_inicio: date,
    data_fim_query: datetime,
    codigos_emp_list: Optional[List[int]],
    descricao_produto: Optional[str],
    marca_produto: Optional[str],
    numero_nota_fiscal: Optional[str]
) -> pd.DataFrame:
    """
    Carrega dados de entradas de produtos (COMPRASPRODUTOS) com base nos filtros fornecidos.
    """
    query_base = f'''
        SELECT
            CP."DATA",        -- Será renomeada no Pandas para C.COL_ENT_DATA
            C.NUMERO_NOTA,    -- Será renomeada no Pandas para C.COL_ENT_NOTA
            CP.CODEMP,        -- Será renomeada no Pandas para C.COL_ENT_CODEMP
            M.MERCADORIA,     -- Será renomeada no Pandas para C.COL_ENT_DESCRICAO
            M.MARCA,          -- Será renomeada no Pandas para C.COL_ENT_MARCA
            CP.QUANTIDADE,    -- Será renomeada no Pandas para C.COL_ENT_QUANTIDADE
            CP.C_UNIT,        -- Será renomeada no Pandas para C.COL_ENT_C_UNIT
            CP.C_UNIT * 1.14 AS "CUSTO",          -- Custo da tabela Mercadorias, será renomeada para C.COL_ENT_CUSTO_M
            CP.C_SUBTOTAL     -- Será renomeada no Pandas para C.COL_ENT_C_SUBTOTAL
        FROM COMPRASPRODUTOS CP
        JOIN MERCADORIAS M ON M.CODEMP = CP.CODEMP
        JOIN COMPRAS C ON C."CODIGO" = CP.COMPRA 
        WHERE 1=1
            AND C.CANCELADA = 'N'
    '''
    params: List[Any] = []

    # Filtro de Data (obrigatório)
    query_base += ' AND CP."DATA" >= ? AND CP."DATA" < ?'
    params.extend([data_inicio, data_fim_query])

    # Filtro DESCRICAO (LIKE)
    if descricao_produto:
        # Usar UPPER para tornar a busca case-insensitive se o seu banco de dados for case-sensitive por padrão
        # Se o DB já for case-insensitive para LIKE, o UPPER pode ser desnecessário.
        query_base += ' AND UPPER(M.MERCADORIA) LIKE UPPER(?)'
        params.append(f"%{descricao_produto}%")

    # Filtro CODEMP (IN)
    if codigos_emp_list: # Se a lista não for nula ou vazia
        if codigos_emp_list: # Checagem dupla para garantir que a lista não é vazia
            codemp_placeholders = ",".join(["?"] * len(codigos_emp_list))
            query_base += f' AND CP.CODEMP IN ({codemp_placeholders})'
            params.extend(codigos_emp_list)

    # Filtro MARCA
    if marca_produto and marca_produto.upper() != "TODAS":
        query_base += ' AND M.MARCA = ?'
        params.append(marca_produto)
    
    # Filtro Nota Fiscal
    if numero_nota_fiscal:
        if numero_nota_fiscal.isdigit():
            query_base += ' AND C.NUMERO_NOTA = ?'
            params.append(int(numero_nota_fiscal))

    # Cláusula ORDER BY
    # Os nomes aqui devem ser os originais da tabela, antes do rename do Pandas
    query_base += ' ORDER BY CP.COMPRA DESC, CP.CODIGO ASC'

    df = _execute_query(query_base, tuple(params))

    if df.empty:
        return pd.DataFrame()

    # Renomear colunas para usar as constantes
    # Assegure-se que os nomes na query SELECT correspondem às chaves aqui.
    # O 'M.CUSTO' é selecionado, vamos renomeá-lo para C.COL_ENT_CUSTO_M
    # Os nomes das colunas no df serão "DATA", "CODEMP", "DESCRICAO", "MARCA", "QUANTIDADE", "C_UNIT", "CUSTO", "C_SUBTOTAL"
    # devido à forma como o _execute_query funciona (ele usa os nomes "AS" se fornecidos, senão os nomes originais)
    # Se não houver "AS" na query SQL, os nomes originais das colunas (ex: CP."DATA") serão as chaves no df.
    # No entanto, pd.read_sql geralmente remove as aspas e pode converter para maiúsculas/minúsculas dependendo do driver/DB.
    # Para ser seguro, vamos verificar as colunas retornadas e renomear.
    # A query SELECT não usa "AS", então os nomes das colunas no DataFrame serão os nomes originais das tabelas (ex: "DATA", "CODEMP").

    rename_map = {
        "DATA": C.COL_ENT_DATA,
        "NUMERO_NOTA": C.COL_ENT_NOTA,
        "CODEMP": C.COL_ENT_CODEMP,
        "MERCADORIA": C.COL_ENT_DESCRICAO,
        "MARCA": C.COL_ENT_MARCA,
        "QUANTIDADE": C.COL_ENT_QUANTIDADE,
        "C_UNIT": C.COL_ENT_C_UNIT, # Custo de Nota Fiscal s
        "CUSTO": C.COL_ENT_CUSTO_M, # Este é M.CUSTO
        "C_SUBTOTAL": C.COL_ENT_C_SUBTOTAL
    }
    df.rename(columns=rename_map, inplace=True)

    # --- Pós-processamento ---
    # Converter DATA para datetime se não estiver já
    if C.COL_ENT_DATA in df.columns:
        df[C.COL_ENT_DATA] = pd.to_datetime(df[C.COL_ENT_DATA], errors='coerce')

    # Converter colunas numéricas e preencher NaNs se necessário
    numeric_cols_to_format = {
        C.COL_ENT_QUANTIDADE: 0, # default para NaN
        C.COL_ENT_C_UNIT: 0.0,
        C.COL_ENT_CUSTO_M: 0.0,
        C.COL_ENT_C_SUBTOTAL: 0.0
    }
    for col, default_value in numeric_cols_to_format.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(default_value)

    # Garantir que CODEMP seja tratado como string para exibição se necessário, ou int
    if C.COL_ENT_CODEMP in df.columns:
        df[C.COL_ENT_CODEMP] = df[C.COL_ENT_CODEMP].astype(str) # Ou int, dependendo de como quer exibir

    # Selecionar e reordenar colunas finais para exibição
    colunas_finais = [
        C.COL_ENT_DATA, C.COL_ENT_NOTA, C.COL_ENT_CODEMP, C.COL_ENT_DESCRICAO, C.COL_ENT_MARCA,
        C.COL_ENT_QUANTIDADE, C.COL_ENT_C_UNIT, C.COL_ENT_CUSTO_M, C.COL_ENT_C_SUBTOTAL
    ]
    # Garantir que apenas colunas existentes e na ordem correta sejam retornadas
    cols_existentes_no_df = [col for col in colunas_finais if col in df.columns]
    return df[cols_existentes_no_df].copy()


######################################################################################



# aba Clientes - última compra 

@st.cache_data(ttl=600, show_spinner="Carregando dados de Última Compra por Cliente...")
def load_ultima_compra_cliente_data(
    cliente_filtro: Optional[str],
    marca_filtro: Optional[str],
    produto_filtro: Optional[str]
) -> pd.DataFrame:
    """
    Carrega a data da última compra para cada cliente, com base nos filtros fornecidos.
    """
    # Placeholders para filtros fixos
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    # Query base com as condições fixas e a agregação
    query_base = f'''
        SELECT
            MAX(V.DATAFATURA) AS MaxData -- Usar um alias simples para MAX
            ,PE.CODEMP AS "Código"
            ,PE.NOME
            ,PE.CNPJ, PE.CPF
            ,PE.FONECOM,PE.FONERES,PE.FONEFAX,PE.FONECEL,PE.FONESAC
        FROM VENDAS V
        JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        LEFT JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        WHERE 1=1
            AND V.CANCELADA = 'N' 
            AND V.NATUREZA = ? -- 'Venda'
            AND VP.CFOP IN ({cfop_placeholders})
            AND V.STATUS = ? -- 'Efetivada'
            AND PE.ATIVO = ? -- 'S'
            AND V.VENDA_FATURADA = ? -- 'S'
            AND VP.MODO = ? -- 'O'
    '''
    params: List[Any] = [
        C.NATUREZA_OPERACAO_VENDA, *C.CFOP_VENDAS_ESTADUAIS,
        C.STATUS_VENDA_EFETIVADA, C.MERCADORIA_ATIVA, # Reutilizando MERCADORIA_ATIVA para PE.ATIVO = 'S'
        C.VENDA_FATURADA_SIM, C.MODO_VENDA_CONCLUIDA
    ]
    # Adicionar filtros dinâmicos
    if cliente_filtro:
        query_base += ' AND UPPER(PE.NOME) LIKE UPPER(?)'
        params.append(f"%{cliente_filtro}%")
    if marca_filtro and marca_filtro.upper() != "TODAS":
        query_base += ' AND M.MARCA = ?'
        params.append(marca_filtro)
    if produto_filtro:
        query_base += ' AND UPPER(M.MERCADORIA) LIKE UPPER(?)'
        params.append(f"%{produto_filtro}%")
    # Adicionar GROUP BY e ORDER BY
    # Agrupar por PE.CODEMP e PE.NOME, conforme query original, para garantir unicidade do cliente
    query_base += '''
        GROUP BY 
            PE.CODEMP, PE.NOME
            ,PE.CNPJ, PE.CPF
            ,PE.FONECOM,PE.FONERES,PE.FONEFAX,PE.FONECEL,PE.FONESAC
        ORDER BY MaxData DESC, PE.NOME ASC
    '''
    df = _execute_query(query_base, tuple(params))
    if df.empty:
        return pd.DataFrame()
    
    # --- Pós-processamento ---
    # Renomear colunas
    rename_map = {
        "MAXDATA": C.COL_ULT_COMPRA_DATA, # O nome da coluna pode variar (MAXDATA, MAX, etc.). Ajuste se necessário.
        "NOME": C.COL_ULT_COMPRA_CLIENTE
    }
    # Tenta renomear sendo flexível com maiúsculas/minúsculas no nome da coluna MAX
    df_cols_lower = [str(col).lower() for col in df.columns]
    if 'maxdata' in df_cols_lower :
        original_max_col = df.columns[df_cols_lower.index('maxdata')]
        rename_map = {original_max_col: C.COL_ULT_COMPRA_DATA, "NOME": C.COL_ULT_COMPRA_CLIENTE}
    elif 'max' in df_cols_lower:
        original_max_col = df.columns[df_cols_lower.index('max')]
        rename_map = {original_max_col: C.COL_ULT_COMPRA_DATA, "NOME": C.COL_ULT_COMPRA_CLIENTE}
    else:
        # Se não encontrar um nome esperado, avisa e tenta usar a primeira coluna
        st.warning("Não foi possível determinar automaticamente o nome da coluna MAX(DATAFATURA). Usando a primeira coluna como Data.")
        if len(df.columns) >= 2:
            rename_map = {df.columns[0]: C.COL_ULT_COMPRA_DATA, df.columns[1]: C.COL_ULT_COMPRA_CLIENTE}
        else:
            st.error("DataFrame retornado não possui colunas suficientes para Data e Cliente.")
            return pd.DataFrame() # Retorna vazio
    df.rename(columns=rename_map, inplace=True)
    # Converter Data para datetime (só a data, sem hora)
    if C.COL_ULT_COMPRA_DATA in df.columns:
        df[C.COL_ULT_COMPRA_DATA] = pd.to_datetime(df[C.COL_ULT_COMPRA_DATA], errors='coerce').dt.date
    # Garantir que Cliente seja string
    if C.COL_ULT_COMPRA_CLIENTE in df.columns:
        df[C.COL_ULT_COMPRA_CLIENTE] = df[C.COL_ULT_COMPRA_CLIENTE].astype(str).fillna('')
    
    # Selecionar e reordenar colunas finais
    colunas_finais = [C.COL_ULT_COMPRA_DATA,"Código", C.COL_ULT_COMPRA_CLIENTE,
                    "CNPJ","CPF","FONECOM","FONERES","FONEFAX","FONECEL","FONESAC" ]
    cols_existentes = [col for col in colunas_finais if col in df.columns]
    return df[cols_existentes].copy()





# aba STANLEY - última compra 

@st.cache_data(ttl=600, show_spinner="Carregando dados de Última Compra por Cliente...")
def load_ultima_compra_cliente_data_stanley(
    cliente_filtro: Optional[str],
    marca_filtro: Optional[str],
    produto_filtro: Optional[str]
) -> pd.DataFrame:
    """
    Carrega a data da última compra para cada cliente, com base nos filtros fornecidos.
    """
    # Placeholders para filtros fixos
    cfop_placeholders = ",".join(["?"] * len(C.CFOP_VENDAS_ESTADUAIS))
    # Query base com as condições fixas e a agregação
    query_base = f'''
        SELECT
            MAX(V.DATAFATURA) AS MaxData -- Usar um alias simples para MAX
            ,PE.CODEMP AS "Código"
            ,PE.NOME
            ,PE.CNPJ, PE.CPF
            ,PE.FONECOM,PE.FONERES,PE.FONEFAX,PE.FONECEL,PE.FONESAC
        FROM VENDAS V
        JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        LEFT JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        WHERE 1=1
            AND V.CANCELADA = 'N' 
            AND V.NATUREZA = ? -- 'Venda'
            AND VP.CFOP IN ({cfop_placeholders})
            AND V.STATUS = ? -- 'Efetivada'
            AND PE.ATIVO = ? -- 'S'
            AND V.VENDA_FATURADA = ? -- 'S'
            AND VP.MODO = ? -- 'O'
            AND PE.NOMEFANTASIA LIKE 'STANLEY%HAIR'
    '''
    params: List[Any] = [
        C.NATUREZA_OPERACAO_VENDA, *C.CFOP_VENDAS_ESTADUAIS,
        C.STATUS_VENDA_EFETIVADA, C.MERCADORIA_ATIVA, # Reutilizando MERCADORIA_ATIVA para PE.ATIVO = 'S'
        C.VENDA_FATURADA_SIM, C.MODO_VENDA_CONCLUIDA
    ]
    # Adicionar filtros dinâmicos
    if cliente_filtro:
        query_base += ' AND UPPER(PE.NOME) LIKE UPPER(?)'
        params.append(f"%{cliente_filtro}%")
    if marca_filtro and marca_filtro.upper() != "TODAS":
        query_base += ' AND M.MARCA = ?'
        params.append(marca_filtro)
    if produto_filtro:
        query_base += ' AND UPPER(M.MERCADORIA) LIKE UPPER(?)'
        params.append(f"%{produto_filtro}%")
    # Adicionar GROUP BY e ORDER BY
    # Agrupar por PE.CODEMP e PE.NOME, conforme query original, para garantir unicidade do cliente
    query_base += '''
        GROUP BY 
            PE.CODEMP, PE.NOME
            ,PE.CNPJ, PE.CPF
            ,PE.FONECOM,PE.FONERES,PE.FONEFAX,PE.FONECEL,PE.FONESAC
        ORDER BY MaxData DESC, PE.NOME ASC
    '''
    df = _execute_query(query_base, tuple(params))
    if df.empty:
        return pd.DataFrame()
    
    # --- Pós-processamento ---
    # Renomear colunas
    rename_map = {
        "MAXDATA": C.COL_ULT_COMPRA_DATA, # O nome da coluna pode variar (MAXDATA, MAX, etc.). Ajuste se necessário.
        "NOME": C.COL_ULT_COMPRA_CLIENTE
    }
    # Tenta renomear sendo flexível com maiúsculas/minúsculas no nome da coluna MAX
    df_cols_lower = [str(col).lower() for col in df.columns]
    if 'maxdata' in df_cols_lower :
        original_max_col = df.columns[df_cols_lower.index('maxdata')]
        rename_map = {original_max_col: C.COL_ULT_COMPRA_DATA, "NOME": C.COL_ULT_COMPRA_CLIENTE}
    elif 'max' in df_cols_lower:
        original_max_col = df.columns[df_cols_lower.index('max')]
        rename_map = {original_max_col: C.COL_ULT_COMPRA_DATA, "NOME": C.COL_ULT_COMPRA_CLIENTE}
    else:
        # Se não encontrar um nome esperado, avisa e tenta usar a primeira coluna
        st.warning("Não foi possível determinar automaticamente o nome da coluna MAX(DATAFATURA). Usando a primeira coluna como Data.")
        if len(df.columns) >= 2:
            rename_map = {df.columns[0]: C.COL_ULT_COMPRA_DATA, df.columns[1]: C.COL_ULT_COMPRA_CLIENTE}
        else:
            st.error("DataFrame retornado não possui colunas suficientes para Data e Cliente.")
            return pd.DataFrame() # Retorna vazio
    df.rename(columns=rename_map, inplace=True)
    
    # Converter Data para datetime (só a data, sem hora)
    if C.COL_ULT_COMPRA_DATA in df.columns:
        df[C.COL_ULT_COMPRA_DATA] = pd.to_datetime(df[C.COL_ULT_COMPRA_DATA], errors='coerce').dt.date
    # Garantir que Cliente seja string
    if C.COL_ULT_COMPRA_CLIENTE in df.columns:
        df[C.COL_ULT_COMPRA_CLIENTE] = df[C.COL_ULT_COMPRA_CLIENTE].astype(str).fillna('')
    
    # Selecionar e reordenar colunas finais
    colunas_finais = [C.COL_ULT_COMPRA_DATA,"Código", C.COL_ULT_COMPRA_CLIENTE,
                    "CNPJ","CPF","FONECOM","FONERES","FONEFAX","FONECEL","FONESAC" ]
    cols_existentes = [col for col in colunas_finais if col in df.columns]
    return df[cols_existentes].copy()



######################################################################################



@st.cache_data
def load_stanley_unidades_data() -> pd.DataFrame:
    """
    Carrega a lista de unidades (clientes) Stanley ativos com sua cidade e UF.
    """
    # Query SQL fixa conforme fornecida
    query = f'''
        SELECT
            P.NOME,
            UPPER(P.MUNICIPIO) AS CidadeUpper, -- Alias para facilitar a renomeação
            P."UF"
        FROM PESSOASEMPRESAS P
        WHERE 1=1
            AND P.ATIVO = 'S'
            AND P.NOMEFANTASIA LIKE 'STANLEY%HAIR'
        ORDER BY P.NOME
    '''
    
    df = _execute_query(query)
    
    if df.empty:
        return pd.DataFrame()
    
    # --- Pós-processamento ---
    # Renomear colunas para usar as constantes
    # Verificar o nome exato da coluna "UF" retornada por _execute_query
    uf_col_name = "UF" # Suposição inicial
    if '"UF"' in df.columns: # Checa se veio com aspas
        uf_col_name = '"UF"'
    elif 'uf' in [str(col).lower() for col in df.columns]: # Checa se veio minúsculo
        uf_col_name = df.columns[[str(col).lower() for col in df.columns].index('uf')]
    rename_map = {
        "NOME": C.COL_ST_UNIDADE_NOME,
        "CIDADEUPPER": C.COL_ST_UNIDADE_CIDADE,
        uf_col_name: C.COL_ST_UNIDADE_UF
    }
    df.rename(columns=rename_map, inplace=True)
    # Garantir que todas as colunas sejam string para exibição
    for col in [C.COL_ST_UNIDADE_NOME, C.COL_ST_UNIDADE_CIDADE, C.COL_ST_UNIDADE_UF]:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna('')
    # Selecionar e reordenar colunas finais
    colunas_finais = [C.COL_ST_UNIDADE_NOME, C.COL_ST_UNIDADE_CIDADE, C.COL_ST_UNIDADE_UF]
    cols_existentes = [col for col in colunas_finais if col in df.columns]
    return df[cols_existentes].copy()


######################################################################################




@st.cache_data(ttl=3600) # Cache por 1 hora para não consultar o DB a cada recarregamento
def get_faturamento_historico_stanley() -> pd.DataFrame:
    """
    Busca o histórico de faturamento, custo, lucro e margem para clientes 'STANLEY%HAIR'.
    Retorna um DataFrame com as colunas: Ano, Mês, Faturamento em Produtos,
    Custo Total, Lucro e Margem.
    """
    query = f"""
    SELECT
        EXTRACT(YEAR FROM V.DATAFATURA) AS "Ano"
        ,EXTRACT(MONTH FROM V.DATAFATURA) AS "Mês"
        ,ROUND(SUM(VP.V_TOT),2) AS "Faturamento em Produtos"
        ,ROUND(SUM((M.CUSTO * VP.QUANTIDADE)),2) AS "Custo Total"
        ,ROUND(SUM(VP.V_TOT) - SUM((M.CUSTO * VP.QUANTIDADE)),2) AS "Lucro"
        ,ROUND((SUM(VP.V_TOT) / SUM(M.CUSTO * VP.QUANTIDADE) - 1) * 100, 0) AS "Margem"
    FROM VENDAS V
        JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        JOIN PESSOASEMPRESAS PE ON PE."CODIGO" = V.CODCLI
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
    WHERE 1=1
        AND V.CANCELADA = 'N'
        AND V.NATUREZA IN ('Venda')
        AND VP.CFOP IN {C.CFOP_VENDAS_ESTADUAIS} -- Usando a constante CFOP
        AND V.STATUS = '{C.STATUS_VENDA_EFETIVADA}' -- Usando a constante STATUS
        AND VP.MODO = '{C.MODO_VENDA_CONCLUIDA}' -- Usando a constante MODO
        AND M.ATIVO = '{C.MERCADORIA_ATIVA}' -- Usando a constante MERCADORIA_ATIVA
        AND PE.NOMEFANTASIA LIKE 'STANLEY%HAIR%'
    GROUP BY "Ano", "Mês"
    ORDER BY "Ano" DESC, "Mês" DESC; -- Adicionando ordenação para melhor visualização
    
    """
    # Não há parâmetros dinâmicos para passar para a query com fdb.
    # No entanto, se no futuro houver, eles seriam passados como uma tupla no segundo argumento.
    df = _execute_query(query)
    
    if df.empty:
        st.info("Nenhum registro de faturamento encontrado para 'STANLEY%HAIR'.")
        return pd.DataFrame()
    
    # --- Pós-processamento e Renomeação de Colunas ---
    # Renomear colunas para usar as constantes.
    # As colunas já vêm com os nomes desejados da query, mas para garantir e usar as constantes,
    # fazemos o mapeamento.
    rename_map = {
        "Ano": C.COL_SF_ANO,
        "Mês": C.COL_SF_MES,
        "Faturamento em Produtos": C.COL_SF_FATURAMENTO_PRODUTOS,
        "Custo Total": C.COL_SF_CUSTO_TOTAL,
        "Lucro": C.COL_SF_LUCRO,
        "Margem": C.COL_SF_MARGEM,
    }
    
    df.rename(columns=rename_map, inplace=True)
    
    # Garantir tipos de dados corretos
    # 'Ano' e 'Mês' devem ser inteiros
    for col in [C.COL_SF_ANO, C.COL_SF_MES]:
        if col in df.columns:
            df[col] = df[col].astype(int)
    
    # Colunas de valores monetários devem ser float
    for col in [C.COL_SF_FATURAMENTO_PRODUTOS, C.COL_SF_CUSTO_TOTAL, C.COL_SF_LUCRO]:
        if col in df.columns:
            df[col] = df[col].astype(float)
    
    # Margem pode ser int ou float, dependendo da precisão desejada.
    # Como o ROUND na query já deixou como 0 casas decimais, int é adequado.
    if C.COL_SF_MARGEM in df.columns:
        df[C.COL_SF_MARGEM] = df[C.COL_SF_MARGEM].astype(int)
    return df



######################################################################################



def get_orcamento_estoque(codigos_venda: List[int]) -> pd.DataFrame:
    """
    Busca o somatório das quantidades de produtos orçados (Stanley) e compara com o estoque atual.

    Args:
        codigos_venda: Uma lista de códigos de venda (orçamentos) para filtrar.

    Returns:
        Um DataFrame pandas com o código do produto, nome, quantidade orçada, estoque e diferença.
        Retorna um DataFrame vazio se nenhum dado for encontrado ou em caso de erro.
    """
    if not codigos_venda:
        st.info("Nenhum código de orçamento fornecido para a consulta Stanley vs. Estoque.")
        return pd.DataFrame()

    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    # Cria a string de placeholders para os códigos de venda
    placeholders = ','.join(['?' for _ in codigos_venda])

    query = f"""
    SELECT
        M.CODEMP AS "{C.COL_CODIGO_BR}"
        ,M.MERCADORIA AS "{C.COL_PRODUTO}"
        ,M.MARCA AS "{C.COL_MARCA}"
        ,SUM(VP.QUANTIDADE) AS "{C.COL_QUANTIDADE}"
        ,ME.SALDO_ESTOQUE AS "{C.COL_ESTOQUE_BR}"
        ,(SUM(VP.QUANTIDADE) - ME.SALDO_ESTOQUE) AS "{C.COL_DIFERENCA}"
    FROM VENDAS V
        JOIN VENDASPRODUTOS VP ON VP.VENDA = V."CODIGO"
        JOIN MERCADORIAS M ON M.CODEMP = VP.CODEMP
        JOIN MERCADORIAS_ESTOQUE ME ON ME.CODIGO_MERCADORIA = M."CODIGO"
    WHERE 1=1
        AND V.CANCELADA = 'N'
        AND VP.MODO <> 'R'
        AND ME.CODIGO_FILIAL = {C.CODIGO_FILIAL_LOJA}
        AND V."CODIGO" IN ({placeholders})
    GROUP BY M.CODEMP, M.MERCADORIA, M.MARCA, ME.SALDO_ESTOQUE
    ORDER BY M.MERCADORIA
    """

    try:
        df = pd.read_sql_query(query, conn, params=tuple(codigos_venda))

        if df.empty:
            st.info("Nenhum registro encontrado para os códigos de orçamento.")
            return pd.DataFrame()

        # Garantir tipos de dados corretos (opcional, mas boa prática)
        for col in [C.COL_QUANTIDADE, 
                    C.COL_ESTOQUE_BR, 
                    C.COL_DIFERENCA]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int) # Assumindo inteiros para quantidades

        return df

    except Exception as e:
        st.error(f"Erro ao buscar dados de orçamento: {e}")
        return pd.DataFrame()



######################################################################################