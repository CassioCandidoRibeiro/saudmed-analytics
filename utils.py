# utils.py
# Módulo para funções utilitárias gerais da aplicação SaudMed Analytics.



######################################################################################




import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
import math
import re
import xlsxwriter # Necessário para engine='xlsxwriter' no to_excel
from typing import List, Tuple, Optional, Union, Any, Dict, Literal
from datetime import date, datetime
import os
# Local
import constants as C



######################################################################################



# --- Funções de Formatação ---

NumericType = Union[int, float, np.number]

@st.cache_data
def formatar_moeda(valor: Optional[NumericType]) -> str:
    """
    Formata um valor numérico como moeda brasileira (R$).
    Args:
        valor: O valor numérico a ser formatado.
    Returns:
        String formatada como R$ XX.XXX,XX ou 'R$ -' em caso de erro/None.
    """
    if valor is None or pd.isna(valor) or not isinstance(valor, (int, float, np.number)):
        return "R$ -"
    try:
        # Converte para float para garantir a formatação correta
        valor_float = float(valor)
        # Formato pt-BR: separador de milhar '.' e decimal ','
        # A sequência de replace garante a ordem correta
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        st.warning(f"Não foi possível formatar o valor '{valor}' como moeda.")
        return "R$ -"



######################################################################################



@st.cache_data
def formatar_percentual(valor: Optional[NumericType], casas_decimais: int = 0) -> str:
    """
    Formata um número como percentual com um número específico de casas decimais.
    Args:
        valor: O valor numérico a ser formatado.
        casas_decimais: O número de casas decimais desejado (padrão 0).
    Returns:
        String formatada como XX% ou '- %' em caso de erro/None/NaN.
    """
    if valor is None or pd.isna(valor) or not isinstance(valor, (int, float, np.number)):
        return "- %"
    try:
        valor_float = float(valor)
        return f"{valor_float:.{casas_decimais}f}%"
    except (ValueError, TypeError):
        st.warning(f"Não foi possível formatar o valor '{valor}' como percentual.")
        return "- %"



######################################################################################



@st.cache_data
def formatar_inteiro(valor: Optional[NumericType]) -> str:
    """
    Formata um número como inteiro com separador de milhar pt-BR.
    Args:
        valor: O valor numérico a ser formatado.
    Returns:
        String formatada como X.XXX ou '-' em caso de erro/None/NaN.
    """
    if valor is None or pd.isna(valor) or not isinstance(valor, (int, float, np.number)):
        return "-"
    try:
        # Arredonda antes de converter para int para lidar com floats
        valor_int = int(round(float(valor)))
        # Formato pt-BR: separador de milhar '.'
        return f"{valor_int:,}".replace(",", ".")
    except (ValueError, TypeError):
        st.warning(f"Não foi possível formatar o valor '{valor}' como inteiro.")
        return "-"



######################################################################################



# --- Funções de Cálculo de Negócio ---

@st.cache_data
def calcular_recomendacao(
    vendas: Optional[NumericType],
    estoque: Optional[NumericType],
    fator: float = C.FATOR_REPOSICAO_ESTOQUE
    ) -> int:
    """
    Calcula a recomendação de compra baseada nas vendas e estoque atual.
    Args:
        vendas: Quantidade de produtos vendidos no período.
        estoque: Quantidade de produtos em estoque.
        fator: Fator de reposição a ser multiplicado pelas vendas (default: C.FATOR_REPOSICAO_ESTOQUE).
    Returns:
        Recomendação de compra (inteiro, arredondado para cima, mínimo 0).
        Retorna 0 se os inputs forem inválidos.
    """
    try:
        # Trata None como 0 e converte para float
        vendas_f = float(vendas if vendas is not None and pd.notna(vendas) else 0.0)
        estoque_f = float(estoque if estoque is not None and pd.notna(estoque) else 0.0)
        # Calcula a recomendação bruta
        recomendacao_bruta = (vendas_f * fator) - estoque_f
        # Retorna o teto (arredonda para cima) se positivo, senão 0. Converte para int.
        return math.ceil(recomendacao_bruta) if recomendacao_bruta > 0 else 0
    except (ValueError, TypeError):
        st.warning(f"Erro ao calcular recomendação com vendas='{vendas}', estoque='{estoque}'. Retornando 0.")
        return 0



######################################################################################



@st.cache_data
def calcular_custo_reverso(
    custo_com_imposto: Optional[NumericType],
    fator: float = C.FATOR_CUSTO_REVERSO_IMPOSTO
    ) -> float:
    """
    Calcula o custo aproximado sem imposto, revertendo um fator multiplicativo.
    Args:
        custo_com_imposto: O custo do produto que inclui o imposto.
        fator: O fator que foi multiplicado para incluir o imposto (default: C.FATOR_CUSTO_REVERSO_IMPOSTO).
    Returns:
        Custo aproximado sem imposto (float, arredondado para 2 casas decimais).
        Retorna 0.0 se o input for inválido ou o fator for 0.
    """
    try:
        # Trata None como 0 e converte para float
        custo_f = float(custo_com_imposto if custo_com_imposto is not None and pd.notna(custo_com_imposto) else 0.0)
        # Evita divisão por zero
        if fator == 0:
            st.warning("Fator de custo reverso é zero. Retornando 0.0.")
            return 0.0
        # Calcula e arredonda
        return round(custo_f / fator, 2)
    except (ValueError, TypeError):
        st.warning(f"Erro ao calcular custo reverso para custo='{custo_com_imposto}'. Retornando 0.0.")
        return 0.0



######################################################################################



# --- Funções de Processamento de Dados ---

def ler_informes_excel(uploaded_file: Any) -> Optional[pd.DataFrame]:
    """
    Lê e processa o arquivo Excel 'Informes' conforme a lógica do backup.
    Aplica skiprows, drop por índice, rename posicional, drop por nome,
    limpeza, conversão de tipos e ordenação.
    Args:
        uploaded_file: O objeto de arquivo carregado pelo Streamlit (st.file_uploader).
    Returns:
        Um DataFrame Pandas processado ou None se ocorrer um erro crítico.
        Retorna um DataFrame vazio se o arquivo for lido mas estiver vazio após limpeza.
    """
    if uploaded_file is None:
        return None
    try:
        # 1. Ler o arquivo Excel pulando linhas iniciais, sem cabeçalho inferido
        df = pd.read_excel(uploaded_file, skiprows=C.INFORMES_SKIP_ROWS, header=None)
        
        # 2. Remover colunas pelos índices especificados
        num_cols_original = df.shape[1]
        indices_validos_para_remover = [idx for idx in C.INFORMES_COLS_TO_DROP_INDICES if idx < num_cols_original]
        if len(indices_validos_para_remover) != len(C.INFORMES_COLS_TO_DROP_INDICES):
            st.warning(f"Aviso: Alguns índices de coluna para remover ({C.INFORMES_COLS_TO_DROP_INDICES}) não existem nas {num_cols_original} colunas lidas do Excel '{uploaded_file.name}'.")
        indices_para_manter = [i for i in range(num_cols_original) if i not in indices_validos_para_remover]
        if not indices_para_manter:
            st.error(f"Erro Crítico: Nenhum índice de coluna válido para manter após aplicar remoção em '{uploaded_file.name}'. Verifique `INFORMES_COLS_TO_DROP_INDICES`.")
            return None
        df = df.iloc[:, indices_para_manter]
        
        # 3. Renomear colunas restantes com nomes temporários
        num_cols_restantes = df.shape[1]
        if num_cols_restantes != len(C._INFORMES_TEMP_COL_NAMES):
            st.error(f"Erro Crítico: Após remover colunas de '{uploaded_file.name}', restaram {num_cols_restantes} colunas, mas esperava {len(C._INFORMES_TEMP_COL_NAMES)} para renomear temporariamente. Verifique `INFORMES_COLS_TO_DROP_INDICES` e o arquivo Excel.")
            return None
        df.columns = C._INFORMES_TEMP_COL_NAMES
        
        # 4. Remover a coluna temporária 'PRECIO' pelo nome
        if C._INFORMES_COL_TO_DROP_NAME in df.columns:
            df = df.drop(C._INFORMES_COL_TO_DROP_NAME, axis=1)
        else:
            st.warning(f"Aviso: Coluna temporária '{C._INFORMES_COL_TO_DROP_NAME}' não encontrada para remoção final em '{uploaded_file.name}'.")
            
        # 5. Renomear colunas finais para os nomes padrão (COL_*)
        if df.shape[1] == len(C.INFORMES_FINAL_COL_NAMES):
            df.columns = C.INFORMES_FINAL_COL_NAMES
        else:
            st.error(f"Erro Crítico: Após remover '{C._INFORMES_COL_TO_DROP_NAME}' de '{uploaded_file.name}', restaram {df.shape[1]} colunas, mas esperava {len(C.INFORMES_FINAL_COL_NAMES)}. Verifique a lógica e o arquivo.")
            return None
        
        # 6. Limpeza de dados: remover linhas com Cod PY nulo, NaN ou vazio/espaços
        df.dropna(subset=[C.COL_CODIGO_PY], inplace=True)
        df = df[df[C.COL_CODIGO_PY].astype(str).str.strip() != '']
        if df.empty:
            st.warning(f"Arquivo '{uploaded_file.name}' parece vazio após limpeza.")
            # Retorna DF vazio para consistência, com as colunas esperadas
            return pd.DataFrame(columns=C.INFORMES_FINAL_COL_NAMES)
        
        # 7. Conversões de Tipo e tratamento de nulos pós-leitura
        df[C.COL_CODIGO_PY] = df[C.COL_CODIGO_PY].astype(str).fillna('')
        for col in [C.COL_VENDAS_PY, C.COL_ESTOQUE_PY]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        for col in [C.COL_PRODUTO_PY, C.COL_MARCA_PY]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')
                
        # 8. Cálculo da Recomendação PY (segurança, caso não tenha sido feito)
        if C.COL_RECOMENDACAO_PY not in df.columns:
            df[C.COL_RECOMENDACAO_PY] = df.apply(
                lambda row: calcular_recomendacao(row.get(C.COL_VENDAS_PY), row.get(C.COL_ESTOQUE_PY)),
                axis=1
            )
        # Calcula texto associado
        if C.COL_TEXTO not in df.columns:
            df[C.COL_TEXTO] = df.apply(
                lambda row: f"{row[C.COL_RECOMENDACAO_PY]} - {row.get(C.COL_PRODUTO_PY, '')}" if row[C.COL_RECOMENDACAO_PY] > 0 else "", axis=1
                )
            
        # 9. Ordenação padrão
        df = df.sort_values(by=[C.COL_MARCA_PY, C.COL_PRODUTO_PY]).reset_index(drop=True)
        return df
    
    except FileNotFoundError:
        st.error(f"Erro: Arquivo '{uploaded_file.name}' não encontrado. O upload pode ter falhado.")
        return None
    except ValueError as ve:
        st.error(f"Erro de valor ao processar '{uploaded_file.name}': {ve}. Verifique o conteúdo das colunas numéricas ou a estrutura do arquivo.")
        return None
    except KeyError as ke:
        st.error(f"Erro de chave (coluna '{ke}' não encontrada) ao processar '{uploaded_file.name}'. Verifique a estrutura do arquivo e os nomes/índices em 'constants.py'.")
        return None
    except Exception as e:
        st.error(C.TEXTO_ERRO_LEITURA_EXCEL.format(e=e))
        st.exception(e) # Log completo no terminal
        return None



######################################################################################



def extrair_pedido_compra(texto_obs: Optional[str]) -> str:
    """
    Extrai um número de pedido de compra de 3 dígitos de uma string de observação.
    Procura pelo padrão 'Pedido de Compra' seguido por 3 dígitos.
    Args:
        texto_obs: A string contendo as observações da nota/venda.
    Returns:
        O número do pedido (3 dígitos) como string, ou "" se não encontrado ou input inválido.
        
    """
    if not texto_obs or pd.isna(texto_obs) or not isinstance(texto_obs, str):
        return ""
    # Regex: 'Pedido de Compra' (case-insensitive), seguido por zero ou mais não-dígitos (\D*),
    # capturando exatamente 3 dígitos (\d{3}).
    match = re.search(r'Pedido de Compra\D*(\d{2,3})', texto_obs, re.IGNORECASE)
    return match.group(1) if match else ""



######################################################################################



def extrair_nome_medicamento(mercadoria: Optional[str]) -> str:
    """
    Extrai o nome limpo do medicamento, removendo prefixos específicos.
    Args:
        mercadoria: O nome original do produto/mercadoria.
    Returns:
        O nome limpo do medicamento como string, ou "" se input inválido.
    """
    if not mercadoria or pd.isna(mercadoria) or not isinstance(mercadoria, str):
        return ""
    nome_limpo = mercadoria.strip() # Remove espaços no início/fim
    # Remove prefixos conhecidos
    if nome_limpo.upper().startswith('CRM - UNID'): # Case-insensitive
        return nome_limpo[10:].strip() # Ajuste no índice para remover 'CRM - UNID'
    elif nome_limpo.upper().startswith('CRM - '): # Case-insensitive
        return nome_limpo[6:].strip() # Ajuste no índice para remover 'CRM - '
    return nome_limpo # Retorna o nome (já com strip) se nenhum prefixo for encontrado



######################################################################################



# --- Funções para Download ---

def dataframe_to_bytes(df: pd.DataFrame, index: bool = False) -> Optional[BytesIO]:
    """
    Converte um DataFrame Pandas para um objeto BytesIO em formato Excel (.xlsx).
    Args:
        df: O DataFrame a ser convertido.
        index: Se True, inclui o índice do DataFrame no arquivo Excel.
    Returns:
        Um objeto BytesIO contendo os dados do Excel, ou None em caso de erro.
    """
    output = BytesIO()
    try:
        # MODIFICAR ESTA LINHA: Adicionar datetime_format e date_format
        with pd.ExcelWriter(output, engine='xlsxwriter',
                            datetime_format='dd/mm/yyyy', # Formato para colunas datetime
                            date_format='dd/mm/yyyy'      # Formato para colunas date
                            ) as writer:
        # FIM DA MODIFICAÇÃO
            df.to_excel(writer, index=index, sheet_name='Dados')
        output.seek(0)
        return output
    except ModuleNotFoundError:
        st.error("Erro ao gerar Excel: Biblioteca 'xlsxwriter' não encontrada. Instale com 'pip install xlsxwriter'.")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao gerar arquivo Excel: {e}")
        st.exception(e)
        return None



######################################################################################



def gerar_botao_download(
    df: Optional[pd.DataFrame],
    file_name: str,
    label: str = "📥 Baixar Tabela (Excel)",
    key_suffix: str = "",
    help_text: Optional[str] = None
    ) -> None:
    """
    Gera um botão de download do Streamlit para um DataFrame, se ele for válido.
    Args:
        df: O DataFrame a ser baixado.
        file_name: O nome base para o arquivo Excel (sem extensão).
        label: O texto a ser exibido no botão.
        key_suffix: Um sufixo para garantir uma chave única para o botão.
        help_text: Texto de ajuda opcional para o botão.
    """
    # Verifica se o DataFrame existe e não está vazio
    if df is not None and not df.empty:
        # Converte o DataFrame para BytesIO
        excel_bytes_io = dataframe_to_bytes(df)
        # Verifica se a conversão foi bem-sucedida
        if excel_bytes_io:
            # Gera o nome completo do arquivo com timestamp
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            full_file_name = f"{file_name}_{timestamp}.xlsx"
            # Cria o botão de download
            st.download_button(
                label=label,
                data=excel_bytes_io, # Passa o objeto BytesIO
                file_name=full_file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_{file_name}{key_suffix}", # Chave única
                help=help_text or f"Clique para baixar os dados da tabela '{file_name}' em formato Excel."
                )
        else:
            st.warning(f"Não foi possível gerar o arquivo '{file_name}.xlsx' para download.")



######################################################################################



# --- Funções Auxiliares de Query ---

def aplicar_filtros_comuns_sql(
    query_base: str,
    params_base: List[Any],
    marca: Optional[str],
    produto: Optional[str],
    categoria: Optional[str]
    ) -> Tuple[str, List[Any]]:
    """
    Adiciona cláusulas WHERE comuns de Marca, Produto e Categoria a uma query SQL base.
    Assume que a query base já possui uma cláusula WHERE 1=1 ou similar
    e que os aliases M para MERCADORIAS e PG para PRODGRUPOS são usados.
    Utiliza placeholders (?) para segurança contra SQL Injection.
    Args:
        query_base: A string da query SQL inicial.
        params_base: A lista inicial de parâmetros para a query base.
        marca: O valor do filtro de marca (ou None ou "Todas").
        produto: O valor do filtro de nome do produto (ou None).
        categoria: O valor do filtro de categoria (ou None ou "Todas").
    Returns:
        Uma tupla contendo a query SQL modificada e a lista de parâmetros atualizada.
    """
    query = query_base
    params = list(params_base) # Cria cópia para não modificar a original
    # Adiciona filtro de Marca se válido
    if marca and marca != "Todas":
        query += " AND M.MARCA = ?"
        params.append(marca)
    # Adiciona filtro de Produto se preenchido
    if produto:
        # Usa LIKE para busca parcial, assume case-insensitivity do DB ou usa UPPER/LOWER se necessário
        query += " AND M.MERCADORIA LIKE ?"
        params.append(f"%{produto}%") # Adiciona wildcards
    # Adiciona filtro de Categoria se válido
    if categoria and categoria != "Todas":
        query += " AND PG.GRUPO = ?"
        params.append(categoria)
    return query, params



######################################################################################



# --- Ajuste manual do valor do Frete Ligeirinho ---

# Função para carregar o valor salvo
def carregar_ajuste():
    try:
        if os.path.exists(C.ARQUIVO_AJUSTE):
            with open(C.ARQUIVO_AJUSTE, 'r') as f:
                return float(f.read())
    except:
        return 0.0  # Valor padrão se ocorrer algum erro
    return 0.0  # Valor padrão se o arquivo não existir
# Função para salvar o valor
def salvar_ajuste(valor):
    with open(C.ARQUIVO_AJUSTE, 'w') as f:
        f.write(str(valor))



######################################################################################



######################################################################################
# --- Funções para Aba INFOSERVE ---


def _ler_fwf_original_style(
    nome_arquivo: str,
    widths: List[int],
    skiprows: int,
    encoding: str,
) -> Optional[pd.DataFrame]:
    """
    Lê um arquivo FWF replicando o método do script original:
    - Lê com header=None, skiprows.
    - Define nomes das colunas pela primeira linha lida (iloc[0]).
    - Remove as duas primeiras linhas lidas (drop [0, 1]).
    - Retorna o DataFrame com nomes de coluna 'sujos' (com espaços) ou None em erro.
    """
    filepath = os.path.join(C.INFOSERVE_PASTA_DADOS, nome_arquivo)
    if not os.path.exists(filepath):
        st.error(C.TEXTO_IS_ERRO_ARQUIVO_NAO_ENCONTRADO.format(filename=nome_arquivo))
        return None
    try:
        df = pd.read_fwf(
            filepath,
            widths=widths,
            encoding=encoding,
            skiprows=skiprows,
            header=None,
            dtype=str # Ler tudo como string primeiro
        )
        if df.empty or len(df) < 2:
            print(f"Debug: Arquivo {nome_arquivo} vazio ou com menos de 2 linhas após skiprows.")
            return pd.DataFrame() # Retorna DF vazio

        # Pega nomes da primeira linha lida (linha 8 do arquivo original)
        nomes_colunas_originais = list(df.iloc[0])
        if len(nomes_colunas_originais) != len(df.columns):
            st.error(C.TEXTO_IS_ERRO_LEITURA.format(filename=nome_arquivo) + f" Discrepância entre widths ({len(widths)}) e colunas lidas ({len(df.columns)}).")
            return None
        # ATRIBUI OS NOMES ORIGINAIS (COM ESPAÇOS)
        df.columns = nomes_colunas_originais

        # Remove as duas primeiras linhas (header original e linha de '---')
        df = df.drop([0, 1]).reset_index(drop=True)
        df = df.dropna(how='all').reset_index(drop=True) # Remove linhas totalmente vazias

        if df.empty:
            print(f"Debug: Arquivo {nome_arquivo} vazio após remover header/separator.")
            return pd.DataFrame()

        print(f"Debug: Arquivo {nome_arquivo} lido e preparado, {len(df)} linhas.")
        return df

    except Exception as e:
        st.error(C.TEXTO_IS_ERRO_LEITURA.format(filename=nome_arquivo) + f" Detalhe: {e}")
        return None

def _find_exact_col_name(df_columns: pd.Index, keyword: str, filename: str) -> Optional[str]:
    """Encontra o nome exato da coluna (com espaços) que contém a keyword."""
    # Tenta encontrar a primeira coluna que contém a keyword (ignorando case e espaços extras)
    col_name = next((col for col in df_columns if keyword.strip().lower() in col.strip().lower()), None)
    if col_name is None:
        st.error(C.TEXTO_IS_ERRO_COLUNA_NAO_ENCONTRADA.format(col_name=keyword, filename=filename))
        print(f"DEBUG: Colunas disponíveis em {filename}: {list(df_columns)}")
        return None
    return col_name


@st.cache_data(show_spinner=C.TEXTO_IS_PROCESSANDO)
def carregar_dados_infoserve_original_final() -> Optional[pd.DataFrame]:
    """
    Versão final que replica fielmente a lógica do script original.
    """
    # 1. Ler movto_productos.txt
    df_movto = _ler_fwf_original_style(
        C.INFOSERVE_ARQUIVO_MOVTO,
        C.INFOSERVE_MOVTO_WIDTHS,
        C.INFOSERVE_SKIPROWS,
        C.INFOSERVE_ENCODING
    )
    if df_movto is None: return None # Erro crítico na leitura
    if df_movto.empty:
        st.info(C.TEXTO_IS_SEM_DADOS + f" (arquivo '{C.INFOSERVE_ARQUIVO_MOVTO}' vazio ou inválido após leitura inicial).")
        return pd.DataFrame() # Arquivo principal vazio
    
    # --- Limpeza inicial movto (replicando script) ---
    try:
        # Encontrar nomes originais (com espaços!)
        col_nota_orig = _find_exact_col_name(df_movto.columns, 'Nota', C.INFOSERVE_ARQUIVO_MOVTO)
        col_codigo_orig = _find_exact_col_name(df_movto.columns, 'Codigo', C.INFOSERVE_ARQUIVO_MOVTO)
        col_clie_orig = _find_exact_col_name(df_movto.columns, 'Clie', C.INFOSERVE_ARQUIVO_MOVTO)
        col_ctd_orig = _find_exact_col_name(df_movto.columns, 'Ctd', C.INFOSERVE_ARQUIVO_MOVTO)
        col_fecha_orig = _find_exact_col_name(df_movto.columns, 'Fecha', C.INFOSERVE_ARQUIVO_MOVTO)
        col_desc_orig = _find_exact_col_name(df_movto.columns, 'Descripcion', C.INFOSERVE_ARQUIVO_MOVTO) # Necessária para drop no final

        # Lista de colunas a serem removidas (nomes originais com espaços)
        cols_to_drop_movto = []
        for keyword in ['Hora', 'Prov Op', 'Referencia', 'Costo', 'N.F', 'User', 'Vend', 'Deposito']:
            col_name = _find_exact_col_name(df_movto.columns, keyword, C.INFOSERVE_ARQUIVO_MOVTO)
            if col_name:
                cols_to_drop_movto.append(col_name)

        if not all([col_nota_orig, col_codigo_orig, col_clie_orig, col_ctd_orig, col_fecha_orig, col_desc_orig]):
            return None # Erro já foi exibido

        # Limpeza SÓ em Nota, Codigo, Clie (como no original)
        for col in [col_nota_orig, col_codigo_orig, col_clie_orig]:
            df_movto[col] = pd.to_numeric(df_movto[col], errors='coerce')
            df_movto = df_movto.dropna(subset=[col])
            if df_movto.empty:
                print(f"Debug: df_movto ficou vazio após dropna em {col}")
                st.info(C.TEXTO_IS_SEM_DADOS + f" (filtrado durante limpeza da coluna '{col.strip()}').")
                return pd.DataFrame()
            df_movto.loc[:, col] = df_movto[col].astype(int)
            
        # Remover colunas que não serão usadas (como no original)
        df_movto = df_movto.drop(columns=cols_to_drop_movto, errors='ignore')
        
        df_geral = df_movto # Começa o DataFrame final
        
    except Exception as e:
        st.error(C.TEXTO_IS_ERRO_PROCESSAMENTO.format(filename=C.INFOSERVE_ARQUIVO_MOVTO) + f" Detalhe: {e}")
        return None


    # 2. Ler e Processar lista_de_clientes.txt (NOME CORRETO)
    df_clientes = _ler_fwf_original_style(
        C.INFOSERVE_ARQUIVO_CLIENTES, # Constante atualizada
        C.INFOSERVE_CLIENTES_WIDTHS, # Constante atualizada
        C.INFOSERVE_SKIPROWS,
        C.INFOSERVE_ENCODING
    )
    df_clientes_final = None # Inicializa
    if df_clientes is None:
        st.warning(f"Aviso: Falha ao ler '{C.INFOSERVE_ARQUIVO_CLIENTES}'. Nomes de clientes não serão incluídos.")
    elif not df_clientes.empty:
        try:
            # Encontrar nomes originais (com espaços!)
            col_cod_cli_orig = _find_exact_col_name(df_clientes.columns, 'Codigo', C.INFOSERVE_ARQUIVO_CLIENTES)
            col_nom_cli_orig = _find_exact_col_name(df_clientes.columns, 'Nombre', C.INFOSERVE_ARQUIVO_CLIENTES)
            
            if not (col_cod_cli_orig and col_nom_cli_orig):
                # Erro já foi exibido em _find_exact_col_name
                pass # Continua sem dados de cliente
            else:
                df_clientes[col_cod_cli_orig] = pd.to_numeric(df_clientes[col_cod_cli_orig], errors='coerce')
                df_clientes = df_clientes.dropna(subset=[col_cod_cli_orig])
                if not df_clientes.empty:
                    df_clientes.loc[:, col_cod_cli_orig] = df_clientes[col_cod_cli_orig].astype(int)
                    # Renomear e selecionar ANTES do merge (como no original)
                    df_clientes_final = df_clientes[[col_cod_cli_orig, col_nom_cli_orig]].rename(columns={
                        col_cod_cli_orig: 'codigo_cliente', # Nome intermediário do script original
                        col_nom_cli_orig: C.COL_IS_NOME_CLIENTE # Nome final
                    }).drop_duplicates(subset=['codigo_cliente'])
                    df_clientes_final.loc[:, C.COL_IS_NOME_CLIENTE] = df_clientes_final[C.COL_IS_NOME_CLIENTE].str.strip()
                else:
                    df_clientes_final = pd.DataFrame(columns=['codigo_cliente', C.COL_IS_NOME_CLIENTE]) # Vazio
        except Exception as e:
            st.error(C.TEXTO_IS_ERRO_PROCESSAMENTO.format(filename=C.INFOSERVE_ARQUIVO_CLIENTES) + f" Detalhe: {e}")
            # df_clientes_final continua None


    # 3. Ler e Processar lista_del_stock.txt
    df_estoque = _ler_fwf_original_style(
        C.INFOSERVE_ARQUIVO_ESTOQUE,
        C.INFOSERVE_ESTOQUE_WIDTHS, # Constante atualizada
        C.INFOSERVE_SKIPROWS,
        C.INFOSERVE_ENCODING
    )
    df_estoque_final = None # Inicializa
    if df_estoque is None:
        st.warning(f"Aviso: Falha ao ler '{C.INFOSERVE_ARQUIVO_ESTOQUE}'. Nomes de produtos não serão incluídos.")
    elif not df_estoque.empty:
        try:
            # Encontrar nomes originais (com espaços!)
            col_cod_prod_orig = _find_exact_col_name(df_estoque.columns, 'Codigo', C.INFOSERVE_ARQUIVO_ESTOQUE)
            col_desc_prod_orig = _find_exact_col_name(df_estoque.columns, 'Descripcion', C.INFOSERVE_ARQUIVO_ESTOQUE)
            
            if not (col_cod_prod_orig and col_desc_prod_orig):
                # Erro já foi exibido
                pass # Continua sem dados de produto
            else:
                df_estoque[col_cod_prod_orig] = pd.to_numeric(df_estoque[col_cod_prod_orig], errors='coerce')
                df_estoque = df_estoque.dropna(subset=[col_cod_prod_orig])
                if not df_estoque.empty:
                    df_estoque.loc[:, col_cod_prod_orig] = df_estoque[col_cod_prod_orig].astype(int)
                    # Renomear e selecionar ANTES do merge (como no original)
                    df_estoque_final = df_estoque[[col_cod_prod_orig, col_desc_prod_orig]].rename(columns={
                        col_cod_prod_orig: 'codigo_producto', # Nome intermediário do script original
                        col_desc_prod_orig: C.COL_IS_NOME_PRODUTO # Nome final
                    }).drop_duplicates(subset=['codigo_producto'])
                    df_estoque_final.loc[:, C.COL_IS_NOME_PRODUTO] = df_estoque_final[C.COL_IS_NOME_PRODUTO].str.strip()
                else:
                    df_estoque_final = pd.DataFrame(columns=['codigo_producto', C.COL_IS_NOME_PRODUTO])
        except Exception as e:
            st.error(C.TEXTO_IS_ERRO_PROCESSAMENTO.format(filename=C.INFOSERVE_ARQUIVO_ESTOQUE) + f" Detalhe: {e}")
            # df_estoque_final continua None


    # 4. Merges (replicando o script original)
    if df_clientes_final is not None:
        try:
            # Merge usando coluna original 'Clie' (com espaços) e 'codigo_cliente'
            df_geral = pd.merge(df_geral, df_clientes_final,
                                left_on=col_clie_orig, # Nome original de df_movto
                                right_on='codigo_cliente', # Nome renomeado de df_clientes
                                how='left')
            # O script original não fazia drop de 'codigo_cliente' aqui, então mantemos
        except KeyError:
            st.error(C.TEXTO_IS_ERRO_MERGE.format(df_name='Clientes'))
            df_geral[C.COL_IS_NOME_CLIENTE] = "Erro Merge" # Placeholder
        except Exception as e:
            st.error(f"Erro inesperado no merge de Clientes: {e}")
            df_geral[C.COL_IS_NOME_CLIENTE] = "Erro Merge"
    else:
        df_geral[C.COL_IS_NOME_CLIENTE] = "N/D"
        
    if df_estoque_final is not None:
        try:
            # Merge usando coluna original 'Codigo' (com espaços) e 'codigo_producto'
            df_geral = pd.merge(df_geral, df_estoque_final,
                                left_on=col_codigo_orig, # Nome original de df_movto
                                right_on='codigo_producto', # Nome renomeado de df_estoque
                                how='left')
            # Drop das colunas redundantes/originais APÓS o merge (como no script)
            df_geral = df_geral.drop(columns=['codigo_producto', col_desc_orig], errors='ignore')
        except KeyError:
            st.error(C.TEXTO_IS_ERRO_MERGE.format(df_name='Estoque'))
            df_geral[C.COL_IS_NOME_PRODUTO] = "Erro Merge"
        except Exception as e:
            st.error(f"Erro inesperado no merge de Estoque: {e}")
            df_geral[C.COL_IS_NOME_PRODUTO] = "Erro Merge"
    else:
        df_geral[C.COL_IS_NOME_PRODUTO] = "N/D"


    # 5. Conversões Finais e Renomeação/Seleção Final (replicando script)
    try:
        # Ctd: .str.replace('.', '').astype(int)
        if col_ctd_orig in df_geral.columns:
            df_geral[C.COL_IS_QTD] = df_geral[col_ctd_orig].astype(str).str.replace('.', '', regex=False).str.strip()
            df_geral[C.COL_IS_QTD] = pd.to_numeric(df_geral[C.COL_IS_QTD], errors='coerce')
            # O script original não fazia dropna aqui, então vamos comentar
            # df_geral = df_geral.dropna(subset=[C.COL_IS_QTD])
            # if df_geral.empty: return pd.DataFrame()
            df_geral.loc[df_geral[C.COL_IS_QTD].notna(), C.COL_IS_QTD] = df_geral.loc[df_geral[C.COL_IS_QTD].notna(), C.COL_IS_QTD].astype(int)
            df_geral[C.COL_IS_QTD] = df_geral[C.COL_IS_QTD].fillna(0) # Preenche NaN com 0 se dropna não for feito
        else:
            st.error(f"Coluna original de Quantidade ('{col_ctd_orig}') não encontrada para conversão final.")
            df_geral[C.COL_IS_QTD] = 0 # Placeholder
            
        # Fecha: pd.to_datetime(..., format='%d/%m/%Y')
        if col_fecha_orig in df_geral.columns:
            df_geral[C.COL_IS_DATA] = pd.to_datetime(df_geral[col_fecha_orig], format='%d/%m/%Y', errors='coerce')
            # O script original NÃO fazia dropna aqui. Manter assim.
        else:
            st.error(f"Coluna original de Data ('{col_fecha_orig}') não encontrada para conversão final.")
            df_geral[C.COL_IS_DATA] = pd.NaT # Placeholder
            
        # Renomear colunas originais limpas para os nomes finais COL_IS_*
        # Nota, Codigo, Clie já foram convertidos e podem ser renomeados
        # (col_codigo_orig e col_clie_orig já foram usados no merge e podem ser removidos ou renomeados agora)
        df_geral = df_geral.rename(columns={
            col_nota_orig: C.COL_IS_NOTA,
            col_codigo_orig: C.COL_IS_COD_PRODUTO, # Renomeia aqui
            col_clie_orig: C.COL_IS_COD_CLIENTE   # Renomeia aqui
        })
        # Remover colunas intermediárias se existirem (ex: 'codigo_cliente' do merge)
        df_geral = df_geral.drop(columns=['codigo_cliente'], errors='ignore')
        
        # Selecionar e reordenar colunas finais (conforme output do script original)
        colunas_finais_desejadas = [
            C.COL_IS_DATA, # Mantida
            # COL_IS_HORA, # Removida no início
            C.COL_IS_NOTA, # Mantida e convertida
            C.COL_IS_COD_CLIENTE, # Mantida e convertida
            C.COL_IS_NOME_CLIENTE, # Adicionada do merge
            C.COL_IS_COD_PRODUTO, # Mantida e convertida
            C.COL_IS_NOME_PRODUTO, # Adicionada do merge
            C.COL_IS_QTD # Mantida e convertida no final
        ]
        colunas_existentes = [col for col in colunas_finais_desejadas if col in df_geral.columns]
        df_final = df_geral[colunas_existentes]
        
        # Ordenar por data (se existir)
        if C.COL_IS_DATA in df_final.columns:
            df_final = df_final.sort_values(by=C.COL_IS_DATA, ascending=False, na_position='last').reset_index(drop=True)
            
        # Verificar se o DataFrame final está vazio
        if df_final.empty:
            st.info(C.TEXTO_IS_SEM_DADOS + " (após todas as etapas de processamento e junção).")
            return pd.DataFrame()
        
        return df_final
    
    except Exception as e:
        st.error(f"Erro durante as conversões finais ou seleção de colunas: {e}")
        return None





######################################################################################



# --- Funções para Anotações da Aba Compras ---
def carregar_anotacoes():
    try:
        if os.path.exists(C.ARQUIVO_ANOTACOES_COMPRAS):
            with open(C.ARQUIVO_ANOTACOES_COMPRAS, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        st.error(f"Erro ao carregar anotações: {e}")
    return ""

def salvar_anotacoes(texto):
    try:
        with open(C.ARQUIVO_ANOTACOES_COMPRAS, 'w', encoding='utf-8') as f:
            f.write(texto)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar anotações: {e}")
        return False



######################################################################################




