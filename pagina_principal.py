# pagina_principal.py
# Dashboard Streamlit para análises da SaudMed


######################################################################################


# Bibliotecas
import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Any, Optional, Tuple, Literal

# Módulos Locais
import constants as C
import utils
import database as db


######################################################################################


# --- Configuração da Página Streamlit ---
APP_TITLE: str = "SaudMed Analytics"
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="❤️", # Ícone da página
    layout="wide",  # Usa layout largo para mais espaço
    initial_sidebar_state="expanded", # Mantém a sidebar aberta inicialmente
    menu_items={ # Personaliza itens do menu
        'Get Help': None, # Remove 'Get Help'
        'Report a bug': None, # Remove 'Report a bug'
        'About': f"""
        {APP_TITLE}
        \nDesenvolvido por Cássio Cândido Ribeiro (2025).
        """
        }
    )


######################################################################################


# --- Funções Auxiliares da Interface do Usuário (UI) ---
def exibir_metricas(colunas: List[st.delta_generator.DeltaGenerator], metricas: Dict[str, str]) -> None:
    """
    Exibe um dicionário de métricas (label: valor_formatado) nas colunas Streamlit fornecidas.
    Args:
        colunas: Uma lista de objetos de coluna do Streamlit (obtidos com st.columns).
        metricas: Um dicionário onde as chaves são os rótulos das métricas e os 
        valores são as strings já formatadas a serem exibidas.
    """
    num_cols = len(colunas)
    metric_items = list(metricas.items())
    num_metrics = len(metric_items)
    
    # Avisa se não houver colunas suficientes, mas tenta exibir o máximo possível
    if num_cols < num_metrics:
        st.warning(f"Layout de colunas ({num_cols}) insuficiente para {num_metrics} métricas. Exibindo as primeiras {num_cols}.")
    
    # Itera pelas métricas e colunas disponíveis
    for i in range(min(num_cols, num_metrics)):
        label, valor_formatado = metric_items[i]
        try:
            # Exibe a métrica na coluna correspondente
            colunas[i].metric(label, valor_formatado)
        except Exception as e:
            # Exibe erro na coluna específica se houver problema
            colunas[i].metric(label, "Erro!")
            st.error(f"Erro ao exibir métrica '{label}': {e}")



######################################################################################




# --- Inicialização do Estado da Sessão (Session State) ---
# Usado para armazenar dados que persistem entre re-execuções (ex: DF do Informes)
if 'df_informes' not in st.session_state:
    st.session_state.df_informes: Optional[pd.DataFrame] = None # DataFrame do arquivo Informes
if 'informes_filename' not in st.session_state:
    st.session_state.informes_filename: Optional[str] = None # Nome do arquivo carregado



######################################################################################



# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    # --- Carregamento dos Filtros de Marca e Categoria ---
    # Usa st.spinner para feedback visual durante o carregamento inicial
    # @st.cache_data é usado nas funções load_*, então o spinner só aparece na primeira vez
    try:
        # Carrega listas de marcas e categorias do banco
        marcas_list: List[str] = ["Todas"] + db.load_marcas()
        categorias_list: List[str] = ["Todas"] + db.load_categorias()
        # Verifica se as listas foram carregadas corretamente
        if len(marcas_list) <= 1:
            st.warning("Não foi possível carregar Marcas do banco.")
        if len(categorias_list) <= 1:
            st.warning("Não foi possível carregar Categorias do banco.")
    except Exception as e:
        # Erro crítico se não conseguir carregar filtros essenciais
        st.error(f"Erro crítico ao carregar filtros do banco: {e}")
        st.stop() # Impede a continuação se filtros falharem
    
    # --- Filtros de Data ---
    data_hoje: date = datetime.now().date()
    
    # Define datas padrão (hoje e 30 dias atrás)
    data_fim_default: date = data_hoje
    data_inicio_default: date = data_hoje - timedelta(days=30)
    
    # Input para Data Inicial
    data_inicio_selecionada: date = st.date_input(
        "Data Inicial",
        value=data_inicio_default,
        min_value=date(2000, 1, 1), # Define um limite mínimo razoável
        max_value=data_hoje,       # Não pode ser no futuro
        format="DD/MM/YYYY",
        help="Primeiro dia a ser incluído na análise."
        )
    
    # Input para Data Final
    data_fim_selecionada: date = st.date_input(
        "Data Final",
        value=data_fim_default,
        min_value=data_inicio_selecionada, # Não pode ser antes da data inicial
        max_value=data_hoje,               # Não pode ser no futuro
        format="DD/MM/YYYY",
        help="Último dia a ser incluído na análise."
        )
    
    # Isso garante que filtros com '<' incluam todo o dia final selecionado
    data_fim_query: datetime = datetime.combine(data_fim_selecionada + timedelta(days=1), time.min)
    # Validação final (embora date_input já restrinja, é uma segurança extra)
    if data_inicio_selecionada > data_fim_selecionada:
        st.error("Datas inválidas! A Data Inicial não pode ser posterior à Data Final.")
        st.stop()
    
    # --- Outros Filtros Globais ---
    # Filtro de marca
    marca_selecionada: str = st.selectbox(
        "Marca", options=marcas_list, index=0,
        help="Selecione uma marca específica ou 'Todas'."
        )
    
    # Filtro de produto
    produto_nome_filtro: str = st.text_input(
        "Produto (Nome)", "",
        help="Digite parte do nome do produto para filtrar."
        ).upper()
    
    # Filtro de categoria
    categoria_selecionada: str = st.selectbox(
        "Categoria", options=categorias_list, index=0,
        help="Selecione uma categoria específica ou 'Todas'."
        )
    
    # --- Upload do Arquivo "Informes" ---
    #st.divider() # Linha divisória visual
    informes_upload: Any = st.file_uploader(
        C.TEXTO_UPLOAD_INFORMES,
        type=["xls"], # Aceita ambos formatos Excel
        help="Faça o upload do arquivo 'Informes.xls' para análises do Paraguai e Geral."
        )
    
    # Processa o arquivo carregado e armazena no estado da sessão
    if informes_upload is not None:
        # Só processa se o arquivo for diferente do que já está no estado (evita reprocessar o mesmo)
        if st.session_state.informes_filename != informes_upload.name:
            with st.spinner(f"Lendo e processando '{informes_upload.name}'..."):
                # Chama a função utilitária para ler e processar o Excel
                df_lido = utils.ler_informes_excel(informes_upload) # Retorna DataFrame ou None
            # Armazena o DataFrame (ou None se falhar) e o nome do arquivo no estado da sessão
            st.session_state.df_informes = df_lido
            st.session_state.informes_filename = informes_upload.name # Atualiza nome mesmo se falhar
            # Feedback para o usuário sobre o resultado da leitura
            if df_lido is not None and not df_lido.empty:
                st.success(f"'{informes_upload.name}' carregado e processado com sucesso!")
            elif df_lido is not None and df_lido.empty:
                # Arquivo lido, mas resultou em DataFrame vazio após limpeza
                st.warning(f"'{informes_upload.name}' lido, mas parece vazio.")
            else:
                # Erro durante a leitura/processamento (mensagem já exibida por ler_informes_excel)
                # Limpa o estado se a leitura falhar completamente
                st.session_state.df_informes = None
                # Mantém o nome do arquivo que falhou para evitar retentar upload idêntico
                # st.session_state.informes_filename = None # Comentado - pode ser útil saber qual falhou



    # Se nenhum arquivo estiver selecionado no uploader atual, mas havia um antes, limpa o estado?
    # Pode ser útil se o usuário quiser "des-selecionar" o arquivo.
    # elif st.session_state.informes_filename is not None:
    #     st.session_state.df_informes = None
    #     st.session_state.informes_filename = None
    #     st.info("Arquivo 'Informes' removido da análise.")



######################################################################################



# --- Layout Principal da Página ---
# st.title(f"❤️ {APP_TITLE}")
# Exibe o período de análise selecionado de forma clara
st.caption(f"Período de Análise: **{data_inicio_selecionada.strftime('%d/%m/%Y')}** a **{data_fim_selecionada.strftime('%d/%m/%Y')}**")

# Cria as abas principais
tab_keys: List[str] = ["compras", "controlados", "clientes", "orcamento", "ligeirinho", "produtos", "infoserve"]
tab_titles: List[str] = ["🛒 COMPRAS", "💊 CONTROLADOS", "😁 CLIENTES", "📄 ORÇAMENTO", "🛵 LIGEIRINHO", "📦 PRODUTOS", "🖥️ INFOSERVE"]
tabs: List[st.delta_generator.DeltaGenerator] = st.tabs(tab_titles)

# Cria um dicionário para acessar as abas por chave (mais legível)
tab_map: Dict[str, st.delta_generator.DeltaGenerator] = dict(zip(tab_keys, tabs))



######################################################################################



#=======================================================================
# ABA 1: COMPRAS
#=======================================================================
with tab_map["compras"]:
    # Abas internas para Brasil, Paraguai e Geral
    brasil_tab, paraguai_tab, geral_tab, geral_sem_stanley = st.tabs(['BRASIL', 'PARAGUAI', 'GERAL (BR + PY)', 'GERAL SEM STANLEY'])
    
    # --- Sub-Aba: Brasil ---
    with brasil_tab:
        # Carrega os dados usando a função do database.py
        # Passa os filtros globais da sidebar
        # O spinner é mostrado automaticamente pela função load_* cacheada
        df_compras_br: pd.DataFrame = db.load_compras_brasil_data(
            data_inicio_selecionada, data_fim_query,
            marca_selecionada, produto_nome_filtro, categoria_selecionada
            )
        # Verifica se o DataFrame foi carregado e não está vazio
        if not df_compras_br.empty:
            # Calcula e formata métricas resumidas ANTES de exibi-las
            try:
                metricas_br: Dict[str, str] = {
                    "Produtos": utils.formatar_inteiro(len(df_compras_br)),
                    "Custo Total Previsto": utils.formatar_moeda(df_compras_br[C.COL_CUSTO_PREVISTO].sum())
                    }
                cols_metricas_br = st.columns(len(metricas_br))
                exibir_metricas(cols_metricas_br, metricas_br)
            except KeyError as e:
                st.error(f"Erro ao calcular métricas BR: Coluna '{e}' não encontrada.")
            except Exception as e:
                st.error(f"Erro inesperado ao calcular métricas BR: {e}")
            # Exibe o DataFrame formatado
            st.dataframe(
                df_compras_br,
                use_container_width=True, # Ocupa toda a largura
                hide_index=True,          # Oculta o índice do Pandas
                column_config={           # Configurações específicas por coluna
                    C.COL_MARCA: st.column_config.TextColumn("Marca"),
                    C.COL_CATEGORIA: st.column_config.TextColumn("Categoria"),
                    C.COL_CODIGO_BR: st.column_config.TextColumn("Código BR"),
                    C.COL_CODIGO_PY: st.column_config.TextColumn("Código PY"),
                    C.COL_PRODUTO: st.column_config.TextColumn("Produto", width="large"),
                    C.COL_CUSTO_UNITARIO: st.column_config.NumberColumn("Custo Unitário", format="R$ %.2f"),
                    C.COL_FORNECEDOR: st.column_config.TextColumn("Último Fornecedor"),
                    C.COL_ULTIMA_ENTRADA: st.column_config.DateColumn("Última Entrada", format="DD/MM/YYYY"),
                    C.COL_PRODUTOS_VENDIDOS: st.column_config.NumberColumn("Produtos Vendidos", format="%d"),
                    C.COL_UNIDADE: st.column_config.TextColumn("Unidade"),
                    C.COL_QTD_VENDAS: st.column_config.NumberColumn("Qtd de Vendas", format="%d"),
                    C.COL_ESTOQUE_BR: st.column_config.NumberColumn("Estoque", format="%d"), 
                    C.COL_RECOMENDACAO_BR: st.column_config.NumberColumn("Recomendação BR", format="%d"),
                    C.COL_CUSTO_PREVISTO: st.column_config.NumberColumn("Custo Previsto", format="R$ %.2f"),
                    C.COL_TEXTO: st.column_config.TextColumn("Texto", width="large"), # Texto da recomendação
                },
                # Define a ordem das colunas para exibição
                column_order=( # Usando tupla para ordem
                    C.COL_MARCA, C.COL_CATEGORIA, C.COL_CODIGO_BR, C.COL_CODIGO_PY, C.COL_PRODUTO,
                    C.COL_CUSTO_UNITARIO, C.COL_FORNECEDOR, C.COL_ULTIMA_ENTRADA, C.COL_PRODUTOS_VENDIDOS, C.COL_UNIDADE, C.COL_QTD_VENDAS,
                    C.COL_ESTOQUE_BR, C.COL_RECOMENDACAO_BR, C.COL_CUSTO_PREVISTO, C.COL_TEXTO
                )
            )
            # Adiciona botão de download
            utils.gerar_botao_download(
                df_compras_br,
                "recomendacao_compras_brasil",
                key_suffix="_br")
        else: # Se df for vazio (query funcionou mas não retornou dados ou houve erro no load)
            st.info(C.TEXTO_NENHUM_DADO)



######################################################################################



# --- Sub-Aba: Paraguai ---
    with paraguai_tab:
        # Pega o DataFrame do 'Informes' do estado da sessão
        df_informes_completo: Optional[pd.DataFrame] = st.session_state.get('df_informes', None)
        # Verifica se o DataFrame do Informes existe e não está vazio
        if df_informes_completo is not None and not df_informes_completo.empty:
            # --- Aplica filtros globais ao DataFrame do Paraguai ---
            # Copia para não modificar o DataFrame original no session_state
            df_filtrado_py = df_informes_completo.copy()
            try:
                if marca_selecionada != "Todas" and C.COL_MARCA_PY in df_filtrado_py.columns:
                    df_filtrado_py = df_filtrado_py[df_filtrado_py[C.COL_MARCA_PY] == marca_selecionada]
                if produto_nome_filtro and C.COL_PRODUTO_PY in df_filtrado_py.columns:
                    # Busca case-insensitive e literal (sem regex por padrão)
                    df_filtrado_py = df_filtrado_py[
                        df_filtrado_py[C.COL_PRODUTO_PY].str.contains(produto_nome_filtro, case=False, regex=False, na=False)
                    ]
                # Filtro de Categoria não se aplica diretamente ao Informes
            except Exception as e:
                st.error(f"Erro ao aplicar filtros nos dados do Paraguai: {e}")
                df_filtrado_py = pd.DataFrame() # Reseta em caso de erro
            # Filtra apenas recomendações positivas para exibição
            # Garante que a coluna de recomendação exista
            if C.COL_RECOMENDACAO_PY in df_filtrado_py.columns:
                df_display_py = df_filtrado_py[df_filtrado_py[C.COL_RECOMENDACAO_PY] > 0].reset_index(drop=True)
            else:
                st.warning(f"Coluna '{C.COL_RECOMENDACAO_PY}' não encontrada nos dados do Informes para filtrar.")
                df_display_py = pd.DataFrame()
            if not df_display_py.empty:# Define as colunas a serem exibidas,
                cols_display_py: List[str] = [
                    C.COL_CODIGO_PY, C.COL_PRODUTO_PY, C.COL_MARCA_PY,
                    C.COL_VENDAS_PY, C.COL_ESTOQUE_PY, C.COL_RECOMENDACAO_PY, C.COL_TEXTO
                    ]
                # Garante que só colunas existentes sejam selecionadas
                cols_existentes_py = [col for col in cols_display_py if col in df_display_py.columns]
                # Exibe métrica
                try:
                    st.metric("Produtos", utils.formatar_inteiro(len(df_display_py)))
                except Exception as e:
                    st.error(f"Erro ao calcular métrica PY: {e}")
                # Exibe DataFrame
                st.dataframe(
                    df_display_py[cols_existentes_py],
                    use_container_width=True,
                    hide_index=True,
                    column_config={ # Nomes e formatos
                        C.COL_CODIGO_PY: st.column_config.TextColumn("Cod PY"),
                        C.COL_PRODUTO_PY: st.column_config.TextColumn("Produto", width="large"),
                        C.COL_MARCA_PY: st.column_config.TextColumn("Marca"),
                        C.COL_VENDAS_PY: st.column_config.NumberColumn("Vendas PY", format="%d"),
                        C.COL_ESTOQUE_PY: st.column_config.NumberColumn("Estoque PY", format="%d"),
                        C.COL_RECOMENDACAO_PY: st.column_config.NumberColumn("Recomendação PY", format="%d"),
                        C.COL_TEXTO: st.column_config.TextColumn("Texto", width="large"),
                        },
                    # Ordem das colunas
                    column_order = tuple(cols_existentes_py) # Usa a ordem definida em cols_display_py
                    )
                # Botão de Download
                utils.gerar_botao_download(df_display_py[cols_existentes_py], "recomendacao_compras_paraguai", key_suffix="_py")
            else:
                # Mensagem se não houver dados após filtros ou se coluna de recomendação faltar
                st.info(C.TEXTO_NENHUM_DADO + " (no arquivo 'Informes' após filtros).")
        elif df_informes_completo is not None: # Se df for vazio mas não None (arquivo lido mas vazio)
            st.info("Arquivo 'Informes' carregado está vazio ou não contém dados válidos após processamento inicial.")
        else:
            # Mensagem se o arquivo 'Informes' não foi carregado
            st.warning(C.TEXTO_INFO_UPLOAD)



######################################################################################



    # --- Sub-Aba: Geral (BR + PY) ---
    with geral_tab:
        # Pega o DF do Informes do estado da sessão
        df_informes_completo: Optional[pd.DataFrame] = st.session_state.get('df_informes', None)
        # Verifica se o Informes foi carregado
        if df_informes_completo is None:
            st.warning(C.TEXTO_INFO_UPLOAD)
        else:
            # Carrega dados do catálogo BR e vendas BR agrupadas, APLICANDO FILTROS GLOBAIS
            # Spinners são mostrados pelas funções load_*
            df_catalogo_br: pd.DataFrame = db.load_catalogo_geral_data(
                marca_selecionada, produto_nome_filtro, categoria_selecionada
                )
            df_vendas_br_agg: pd.DataFrame = db.load_vendas_brasil_agrupado_data(
                data_inicio_selecionada, data_fim_query,
                marca_selecionada, produto_nome_filtro, categoria_selecionada
                )
            # Verifica se os dados BR foram carregados
            if df_catalogo_br.empty:
                st.warning("Não foi possível carregar o catálogo de produtos BR para a análise geral (verifique filtros ou conexão).")
            # df_vendas_br_agg pode estar vazio, o que é normal
            # Não precisa checar df_vendas_br_agg por None, pois db.load_* retorna DF vazio em erro
            else:
                # --- Início da Lógica de Merge e Cálculo Geral  ---
                try:
                    # Começa com o catálogo BR
                    df_geral = df_catalogo_br.copy()
                    # Renomeia Custo Unitário para 'Custo'
                    if C.COL_CUSTO_UNITARIO in df_geral.columns:
                        df_geral.rename(columns={C.COL_CUSTO_UNITARIO: C.COL_CUSTO_GERAL}, inplace=True)
                    else:
                        st.warning(f"Coluna '{C.COL_CUSTO_UNITARIO}' não encontrada no catálogo BR para renomear para '{C.COL_CUSTO_GERAL}'.")
                        # Define a coluna com 0 para evitar erros posteriores, se possível
                        if C.COL_CUSTO_GERAL not in df_geral.columns: df_geral[C.COL_CUSTO_GERAL] = 0.0
                    # 1. Adiciona Vendas BR
                    if not df_vendas_br_agg.empty:
                        df_geral = pd.merge(df_geral, df_vendas_br_agg, on=C.COL_CODIGO_BR, how='left')
                        # Preenche NaNs em Vendas BR (que surgem do merge left) com 0
                        df_geral[C.COL_VENDAS_BR] = df_geral[C.COL_VENDAS_BR].fillna(0).astype(int)
                    else:
                        # Se não houver vendas BR, adiciona a coluna com zeros
                        df_geral[C.COL_VENDAS_BR] = 0
                    # --- Calcula recomendações ---
                    # Garante que as colunas de input existam e sejam numéricas
                    df_geral[C.COL_VENDAS_BR] = pd.to_numeric(df_geral[C.COL_VENDAS_BR], errors='coerce').fillna(0)
                    df_geral[C.COL_ESTOQUE_BR] = pd.to_numeric(df_geral[C.COL_ESTOQUE_BR], errors='coerce').fillna(0)
                    # Calcula Recomendação BR diretamente (permitindo negativos), depois aplica ceil
                    df_geral[C.COL_RECOMENDACAO_BR] = (
                        df_geral[C.COL_VENDAS_BR] * C.FATOR_REPOSICAO_ESTOQUE - df_geral[C.COL_ESTOQUE_BR]
                    )
                    # Aplica teto (math.ceil) elemento a elemento, tratando possíveis NaNs que podem surgir
                    df_geral[C.COL_RECOMENDACAO_BR] = df_geral[C.COL_RECOMENDACAO_BR].apply(lambda x: math.ceil(x) if pd.notna(x) else 0).astype(int)
                    # 2. Adiciona Dados PY (Estoque, Vendas)
                    cols_py_merge = [C.COL_CODIGO_PY, C.COL_ESTOQUE_PY, C.COL_VENDAS_PY] # Pega Vendas e Estoque PY
                    cols_py_existentes = [col for col in cols_py_merge if col in df_informes_completo.columns]
                    if C.COL_CODIGO_PY not in cols_py_existentes:
                        st.error(f"Coluna chave '{C.COL_CODIGO_PY}' não encontrada no arquivo Informes. Impossível fazer merge.")
                        st.stop()
                    vendas_py_sel = df_informes_completo[cols_py_existentes].copy()
                    vendas_py_sel[C.COL_CODIGO_PY] = vendas_py_sel[C.COL_CODIGO_PY].astype(str).fillna('')
                    df_geral[C.COL_CODIGO_PY] = df_geral[C.COL_CODIGO_PY].astype(str).fillna('')
                    df_geral = pd.merge(df_geral, vendas_py_sel, on=C.COL_CODIGO_PY, how='left')
                    # Preenche NaNs das colunas do PY com 0
                    fill_py = {C.COL_VENDAS_PY: 0, C.COL_ESTOQUE_PY: 0}
                    df_geral.fillna(fill_py, inplace=True)
                    for col in fill_py:
                        if col in df_geral.columns:
                            df_geral[col] = pd.to_numeric(df_geral[col], errors='coerce').fillna(0).astype(int)
                    # Calcula Recomendação PY diretamente (permitindo negativos), depois aplica ceil
                    df_geral[C.COL_RECOMENDACAO_PY] = (
                        df_geral[C.COL_VENDAS_PY] * C.FATOR_REPOSICAO_ESTOQUE - df_geral[C.COL_ESTOQUE_PY]
                        )
                    df_geral[C.COL_RECOMENDACAO_PY] = df_geral[C.COL_RECOMENDACAO_PY].apply(lambda x: math.ceil(x) if pd.notna(x) else 0).astype(int)
                    # 3. Cálculos Consolidados (Usando as recomendações calculadas acima)
                    # Tem p/ PY? (Agora usa Rec BR que pode ser < 0)
                    cond_tem_py = (df_geral[C.COL_RECOMENDACAO_PY] > 0) & (df_geral[C.COL_RECOMENDACAO_BR] < 0) & (df_geral[C.COL_ESTOQUE_BR] > 0)
                    df_geral[C.COL_TEM_P_PY] = np.where(cond_tem_py, "Sim", "Não")
                    # Quanto comprar?
                    df_geral[C.COL_QUANTO_COMPRAR] = np.where(
                        (df_geral[C.COL_RECOMENDACAO_PY] <= 0) & (df_geral[C.COL_RECOMENDACAO_BR] > 0), # PY não precisa, BR precisa
                        df_geral[C.COL_RECOMENDACAO_BR],
                        # Outros casos: Soma das recomendações (pode ser negativo se ambos forem negativos)
                        df_geral[C.COL_RECOMENDACAO_PY] + df_geral[C.COL_RECOMENDACAO_BR]
                        )
                    # Arredonda para cima APENAS se for positivo, senão 0. Garante inteiro.
                    df_geral[C.COL_QUANTO_COMPRAR] = df_geral[C.COL_QUANTO_COMPRAR].apply(lambda x: math.ceil(x) if x > 0 else 0).astype(int)
                    # Custo Previsto (Baseado no Quanto Comprar e Custo Unitário GERAL)
                    df_geral[C.COL_CUSTO_PREVISTO] = df_geral[C.COL_QUANTO_COMPRAR] * df_geral[C.COL_CUSTO_GERAL]
                    # Texto para Comprar (Whatsapp Fornecedor)
                    df_geral[C.COL_UNIDADE] = df_geral[C.COL_UNIDADE].astype(str).fillna('') # Garante unidade como string
                    df_geral[C.COL_COMPRAR_TEXTO] = np.where(
                        df_geral[C.COL_QUANTO_COMPRAR] > 0,
                        df_geral[C.COL_QUANTO_COMPRAR].astype(str) + " " + df_geral[C.COL_UNIDADE] + " - " + df_geral[C.COL_PRODUTO].astype(str),
                        ""
                        )
                    # Texto para Separar p/ PY
                    quantidade_py_separar = np.where(
                        (df_geral[C.COL_RECOMENDACAO_BR] < 0), # BR tem excesso (Rec BR é negativa)
                        np.minimum(df_geral[C.COL_RECOMENDACAO_PY], - df_geral[C.COL_RECOMENDACAO_BR]), # Mínimo(Necessidade PY, Excesso BR positivo)
                        df_geral[C.COL_RECOMENDACAO_PY] # Se BR não tem excesso, manda o que PY precisa
                        )
                    # Garante que a quantidade a separar seja >= 0 e inteira
                    quantidade_py_separar = np.maximum(quantidade_py_separar, 0).astype(int)
                    # Condição para gerar o texto (Rec PY > 0 E Tem p/ PY? == Sim)
                    condicao_separar_texto = (df_geral[C.COL_RECOMENDACAO_PY] > 0) & (df_geral[C.COL_TEM_P_PY] == 'Sim')
                    df_geral[C.COL_SEPARAR_P_PY] = np.where(
                        condicao_separar_texto,
                        quantidade_py_separar.astype(str) + " " + df_geral[C.COL_UNIDADE] + " - " + df_geral[C.COL_PRODUTO].astype(str),
                        "" # String vazia se a condição não for atendida
                        )
                    # --- Fim da Lógica Geral ---
                    # Ordena o DataFrame final
                    df_geral = df_geral.sort_values(by=[C.COL_MARCA, C.COL_PRODUTO]).reset_index(drop=True)
                    # --- Exibição da Aba Geral ---
                    # Métricas
                    metricas_geral: Dict[str, str] = {
                        "Produtos": utils.formatar_inteiro(len(df_geral)),
                        "Custo Total Previsto": utils.formatar_moeda(df_geral[C.COL_CUSTO_PREVISTO].sum())
                        }
                    cols_metricas_geral = st.columns(len(metricas_geral))
                    exibir_metricas(cols_metricas_geral, metricas_geral)
                    # Define as colunas a serem exibidas na tabela geral e a ordem,
                    colunas_exib_geral: List[str] = [
                        C.COL_MARCA, C.COL_PRODUTO, C.COL_CATEGORIA, C.COL_CODIGO_BR, C.COL_CODIGO_PY,
                        C.COL_CUSTO_GERAL, C.COL_FORNECEDOR, C.COL_ULTIMA_ENTRADA, C.COL_UNIDADE,
                        C.COL_ESTOQUE_BR, C.COL_VENDAS_BR, C.COL_RECOMENDACAO_BR,
                        C.COL_ESTOQUE_PY, C.COL_VENDAS_PY, C.COL_RECOMENDACAO_PY,
                        C.COL_TEM_P_PY, C.COL_QUANTO_COMPRAR, C.COL_CUSTO_PREVISTO,
                        C.COL_COMPRAR_TEXTO, C.COL_SEPARAR_P_PY
                        ]
                    # Garante que só colunas existentes sejam selecionadas
                    cols_existentes_geral = [col for col in colunas_exib_geral if col in df_geral.columns]
                    # Exibe o DataFrame Geral
                    st.dataframe(
                        df_geral[cols_existentes_geral],
                        hide_index=True,
                        use_container_width=True,
                        column_config={ # Configurações de formatação e títulos das colunas
                            C.COL_MARCA: st.column_config.TextColumn("Marca"),
                            C.COL_PRODUTO: st.column_config.TextColumn("Produto", width="large"),
                            C.COL_CATEGORIA: st.column_config.TextColumn("Categoria"),
                            C.COL_CODIGO_BR: st.column_config.TextColumn("Cod BR"),
                            C.COL_CODIGO_PY: st.column_config.TextColumn("Cod PY"),
                            C.COL_CUSTO_GERAL: st.column_config.NumberColumn("Custo", format="R$ %.2f"), # Título "Custo"
                            C.COL_FORNECEDOR: st.column_config.TextColumn("Último Fornecedor"),
                            C.COL_ULTIMA_ENTRADA: st.column_config.DateColumn("Última Entrada", format="DD/MM/YYYY"),
                            C.COL_UNIDADE: st.column_config.TextColumn("Unidade"),
                            C.COL_ESTOQUE_BR: st.column_config.NumberColumn("Estoque BR", format="%d"),
                            C.COL_VENDAS_BR: st.column_config.NumberColumn("Vendas BR", format="%d"),
                            C.COL_RECOMENDACAO_BR: st.column_config.NumberColumn("Recomendação BR", format="%d"), # Exibe valor que pode ser negativo
                            C.COL_ESTOQUE_PY: st.column_config.NumberColumn("Estoque PY", format="%d"),
                            C.COL_VENDAS_PY: st.column_config.NumberColumn("Vendas PY", format="%d"),
                            C.COL_RECOMENDACAO_PY: st.column_config.NumberColumn("Recomendação PY", format="%d"), # Exibe valor que pode ser negativo
                            C.COL_TEM_P_PY: st.column_config.TextColumn("Tem p/ PY?"),
                            C.COL_QUANTO_COMPRAR: st.column_config.NumberColumn("Quanto comprar?", format="%d"), # Este é sempre >= 0
                            C.COL_CUSTO_PREVISTO: st.column_config.NumberColumn("Custo Previsto", format="R$ %.2f"),
                            C.COL_COMPRAR_TEXTO: st.column_config.TextColumn("Comprar", width="large"),
                            C.COL_SEPARAR_P_PY: st.column_config.TextColumn("Separar p/ PY", width="large"),
                            },
                        column_order=tuple(cols_existentes_geral) # Usa a ordem definida acima
                        )
                    # Botão de Download para a tabela geral
                    utils.gerar_botao_download(df_geral[cols_existentes_geral], "recomendacao_compras_geral", key_suffix="_geral")
                except Exception as e:
                    st.error(f"Erro ao processar dados gerais de compras: {e}")
                    st.exception(e)
    
    
    
    # --- Sub-Aba: GERAL SEM STANLEY ---
    with geral_sem_stanley:
        # Pega o DF do Informes do estado da sessão
        df_informes_completo: Optional[pd.DataFrame] = st.session_state.get('df_informes', None)
        # Verifica se o Informes foi carregado
        if df_informes_completo is None:
            st.warning(C.TEXTO_INFO_UPLOAD)
        else:
            # Carrega dados do catálogo BR e vendas BR agrupadas, APLICANDO FILTROS GLOBAIS
            # Spinners são mostrados pelas funções load_*
            df_catalogo_br: pd.DataFrame = db.load_catalogo_geral_data(
                marca_selecionada, produto_nome_filtro, categoria_selecionada
                )
            df_vendas_br_agg: pd.DataFrame = db.load_vendas_brasil_agrupado_data_menos_stanley(
                data_inicio_selecionada, data_fim_query,
                marca_selecionada, produto_nome_filtro, categoria_selecionada
                )
            # Verifica se os dados BR foram carregados
            if df_catalogo_br.empty:
                st.warning("Não foi possível carregar o catálogo de produtos BR para a análise geral (verifique filtros ou conexão).")
            # df_vendas_br_agg pode estar vazio, o que é normal
            # Não precisa checar df_vendas_br_agg por None, pois db.load_* retorna DF vazio em erro
            else:
                # --- Início da Lógica de Merge e Cálculo Geral  ---
                try:
                    # Começa com o catálogo BR
                    df_geral = df_catalogo_br.copy()
                    # Renomeia Custo Unitário para 'Custo'
                    if C.COL_CUSTO_UNITARIO in df_geral.columns:
                        df_geral.rename(columns={C.COL_CUSTO_UNITARIO: C.COL_CUSTO_GERAL}, inplace=True)
                    else:
                        st.warning(f"Coluna '{C.COL_CUSTO_UNITARIO}' não encontrada no catálogo BR para renomear para '{C.COL_CUSTO_GERAL}'.")
                        # Define a coluna com 0 para evitar erros posteriores, se possível
                        if C.COL_CUSTO_GERAL not in df_geral.columns: df_geral[C.COL_CUSTO_GERAL] = 0.0
                    # 1. Adiciona Vendas BR
                    if not df_vendas_br_agg.empty:
                        df_geral = pd.merge(df_geral, df_vendas_br_agg, on=C.COL_CODIGO_BR, how='left')
                        # Preenche NaNs em Vendas BR (que surgem do merge left) com 0
                        df_geral[C.COL_VENDAS_BR] = df_geral[C.COL_VENDAS_BR].fillna(0).astype(int)
                    else:
                        # Se não houver vendas BR, adiciona a coluna com zeros
                        df_geral[C.COL_VENDAS_BR] = 0
                    # --- Calcula recomendações ---
                    # Garante que as colunas de input existam e sejam numéricas
                    df_geral[C.COL_VENDAS_BR] = pd.to_numeric(df_geral[C.COL_VENDAS_BR], errors='coerce').fillna(0)
                    df_geral[C.COL_ESTOQUE_BR] = pd.to_numeric(df_geral[C.COL_ESTOQUE_BR], errors='coerce').fillna(0)
                    # Calcula Recomendação BR diretamente (permitindo negativos), depois aplica ceil
                    df_geral[C.COL_RECOMENDACAO_BR] = (
                        df_geral[C.COL_VENDAS_BR] * C.FATOR_REPOSICAO_ESTOQUE - df_geral[C.COL_ESTOQUE_BR]
                    )
                    # Aplica teto (math.ceil) elemento a elemento, tratando possíveis NaNs que podem surgir
                    df_geral[C.COL_RECOMENDACAO_BR] = df_geral[C.COL_RECOMENDACAO_BR].apply(lambda x: math.ceil(x) if pd.notna(x) else 0).astype(int)
                    # 2. Adiciona Dados PY (Estoque, Vendas)
                    cols_py_merge = [C.COL_CODIGO_PY, C.COL_ESTOQUE_PY, C.COL_VENDAS_PY] # Pega Vendas e Estoque PY
                    cols_py_existentes = [col for col in cols_py_merge if col in df_informes_completo.columns]
                    if C.COL_CODIGO_PY not in cols_py_existentes:
                        st.error(f"Coluna chave '{C.COL_CODIGO_PY}' não encontrada no arquivo Informes. Impossível fazer merge.")
                        st.stop()
                    vendas_py_sel = df_informes_completo[cols_py_existentes].copy()
                    vendas_py_sel[C.COL_CODIGO_PY] = vendas_py_sel[C.COL_CODIGO_PY].astype(str).fillna('')
                    df_geral[C.COL_CODIGO_PY] = df_geral[C.COL_CODIGO_PY].astype(str).fillna('')
                    df_geral = pd.merge(df_geral, vendas_py_sel, on=C.COL_CODIGO_PY, how='left')
                    # Preenche NaNs das colunas do PY com 0
                    fill_py = {C.COL_VENDAS_PY: 0, C.COL_ESTOQUE_PY: 0}
                    df_geral.fillna(fill_py, inplace=True)
                    for col in fill_py:
                        if col in df_geral.columns:
                            df_geral[col] = pd.to_numeric(df_geral[col], errors='coerce').fillna(0).astype(int)
                    # Calcula Recomendação PY diretamente (permitindo negativos), depois aplica ceil
                    df_geral[C.COL_RECOMENDACAO_PY] = (
                        df_geral[C.COL_VENDAS_PY] * C.FATOR_REPOSICAO_ESTOQUE - df_geral[C.COL_ESTOQUE_PY]
                        )
                    df_geral[C.COL_RECOMENDACAO_PY] = df_geral[C.COL_RECOMENDACAO_PY].apply(lambda x: math.ceil(x) if pd.notna(x) else 0).astype(int)
                    # 3. Cálculos Consolidados (Usando as recomendações calculadas acima)
                    # Tem p/ PY? (Agora usa Rec BR que pode ser < 0)
                    cond_tem_py = (df_geral[C.COL_RECOMENDACAO_PY] > 0) & (df_geral[C.COL_RECOMENDACAO_BR] < 0) & (df_geral[C.COL_ESTOQUE_BR] > 0)
                    df_geral[C.COL_TEM_P_PY] = np.where(cond_tem_py, "Sim", "Não")
                    # Quanto comprar?
                    df_geral[C.COL_QUANTO_COMPRAR] = np.where(
                        (df_geral[C.COL_RECOMENDACAO_PY] <= 0) & (df_geral[C.COL_RECOMENDACAO_BR] > 0), # PY não precisa, BR precisa
                        df_geral[C.COL_RECOMENDACAO_BR],
                        # Outros casos: Soma das recomendações (pode ser negativo se ambos forem negativos)
                        df_geral[C.COL_RECOMENDACAO_PY] + df_geral[C.COL_RECOMENDACAO_BR]
                        )
                    # Arredonda para cima APENAS se for positivo, senão 0. Garante inteiro.
                    df_geral[C.COL_QUANTO_COMPRAR] = df_geral[C.COL_QUANTO_COMPRAR].apply(lambda x: math.ceil(x) if x > 0 else 0).astype(int)
                    # Custo Previsto (Baseado no Quanto Comprar e Custo Unitário GERAL)
                    df_geral[C.COL_CUSTO_PREVISTO] = df_geral[C.COL_QUANTO_COMPRAR] * df_geral[C.COL_CUSTO_GERAL]
                    # Texto para Comprar (Whatsapp Fornecedor)
                    df_geral[C.COL_UNIDADE] = df_geral[C.COL_UNIDADE].astype(str).fillna('') # Garante unidade como string
                    df_geral[C.COL_COMPRAR_TEXTO] = np.where(
                        df_geral[C.COL_QUANTO_COMPRAR] > 0,
                        df_geral[C.COL_QUANTO_COMPRAR].astype(str) + " " + df_geral[C.COL_UNIDADE] + " - " + df_geral[C.COL_PRODUTO].astype(str),
                        ""
                        )
                    # Texto para Separar p/ PY
                    quantidade_py_separar = np.where(
                        (df_geral[C.COL_RECOMENDACAO_BR] < 0), # BR tem excesso (Rec BR é negativa)
                        np.minimum(df_geral[C.COL_RECOMENDACAO_PY], - df_geral[C.COL_RECOMENDACAO_BR]), # Mínimo(Necessidade PY, Excesso BR positivo)
                        df_geral[C.COL_RECOMENDACAO_PY] # Se BR não tem excesso, manda o que PY precisa
                        )
                    # Garante que a quantidade a separar seja >= 0 e inteira
                    quantidade_py_separar = np.maximum(quantidade_py_separar, 0).astype(int)
                    # Condição para gerar o texto (Rec PY > 0 E Tem p/ PY? == Sim)
                    condicao_separar_texto = (df_geral[C.COL_RECOMENDACAO_PY] > 0) & (df_geral[C.COL_TEM_P_PY] == 'Sim')
                    df_geral[C.COL_SEPARAR_P_PY] = np.where(
                        condicao_separar_texto,
                        quantidade_py_separar.astype(str) + " " + df_geral[C.COL_UNIDADE] + " - " + df_geral[C.COL_PRODUTO].astype(str),
                        "" # String vazia se a condição não for atendida
                        )
                    # --- Fim da Lógica Geral ---
                    # Ordena o DataFrame final
                    df_geral = df_geral.sort_values(by=[C.COL_MARCA, C.COL_PRODUTO]).reset_index(drop=True)
                    # --- Exibição da Aba Geral ---
                    # Métricas
                    metricas_geral: Dict[str, str] = {
                        "Produtos": utils.formatar_inteiro(len(df_geral)),
                        "Custo Total Previsto": utils.formatar_moeda(df_geral[C.COL_CUSTO_PREVISTO].sum())
                        }
                    cols_metricas_geral = st.columns(len(metricas_geral))
                    exibir_metricas(cols_metricas_geral, metricas_geral)
                    # Define as colunas a serem exibidas na tabela geral e a ordem,
                    colunas_exib_geral: List[str] = [
                        C.COL_MARCA, C.COL_PRODUTO, C.COL_CATEGORIA, C.COL_CODIGO_BR, C.COL_CODIGO_PY,
                        C.COL_CUSTO_GERAL,C.COL_FORNECEDOR, C.COL_ULTIMA_ENTRADA,
                        C.COL_UNIDADE,
                        C.COL_ESTOQUE_BR, C.COL_VENDAS_BR, C.COL_RECOMENDACAO_BR,
                        C.COL_ESTOQUE_PY, C.COL_VENDAS_PY, C.COL_RECOMENDACAO_PY,
                        C.COL_TEM_P_PY, C.COL_QUANTO_COMPRAR, C.COL_CUSTO_PREVISTO,
                        C.COL_COMPRAR_TEXTO, C.COL_SEPARAR_P_PY
                        ]
                    # Garante que só colunas existentes sejam selecionadas
                    cols_existentes_geral = [col for col in colunas_exib_geral if col in df_geral.columns]
                    # Exibe o DataFrame Geral
                    st.dataframe(
                        df_geral[cols_existentes_geral],
                        hide_index=True,
                        use_container_width=True,
                        column_config={ # Configurações de formatação e títulos das colunas
                            C.COL_MARCA: st.column_config.TextColumn("Marca"),
                            C.COL_PRODUTO: st.column_config.TextColumn("Produto", width="large"),
                            C.COL_CATEGORIA: st.column_config.TextColumn("Categoria"),
                            C.COL_CODIGO_BR: st.column_config.TextColumn("Cod BR"),
                            C.COL_CODIGO_PY: st.column_config.TextColumn("Cod PY"),
                            C.COL_CUSTO_GERAL: st.column_config.NumberColumn("Custo", format="R$ %.2f"), # Título "Custo"
                            C.COL_FORNECEDOR: st.column_config.TextColumn("Último Fornecedor"),
                            C.COL_ULTIMA_ENTRADA: st.column_config.DateColumn("Última Entrada", format="DD/MM/YYYY"),
                            C.COL_UNIDADE: st.column_config.TextColumn("Unidade"),
                            C.COL_ESTOQUE_BR: st.column_config.NumberColumn("Estoque BR", format="%d"),
                            C.COL_VENDAS_BR: st.column_config.NumberColumn("Vendas BR", format="%d"),
                            C.COL_RECOMENDACAO_BR: st.column_config.NumberColumn("Recomendação BR", format="%d"), # Exibe valor que pode ser negativo
                            C.COL_ESTOQUE_PY: st.column_config.NumberColumn("Estoque PY", format="%d"),
                            C.COL_VENDAS_PY: st.column_config.NumberColumn("Vendas PY", format="%d"),
                            C.COL_RECOMENDACAO_PY: st.column_config.NumberColumn("Recomendação PY", format="%d"), # Exibe valor que pode ser negativo
                            C.COL_TEM_P_PY: st.column_config.TextColumn("Tem p/ PY?"),
                            C.COL_QUANTO_COMPRAR: st.column_config.NumberColumn("Quanto comprar?", format="%d"), # Este é sempre >= 0
                            C.COL_CUSTO_PREVISTO: st.column_config.NumberColumn("Custo Previsto", format="R$ %.2f"),
                            C.COL_COMPRAR_TEXTO: st.column_config.TextColumn("Comprar", width="large"),
                            C.COL_SEPARAR_P_PY: st.column_config.TextColumn("Separar p/ PY", width="large"),
                            },
                        column_order=tuple(cols_existentes_geral) # Usa a ordem definida acima
                        )
                    # Botão de Download para a tabela geral
                    utils.gerar_botao_download(df_geral[cols_existentes_geral], "recomendacao_compras_geral_sem stanley", key_suffix="_geral")
                except Exception as e:
                    st.error(f"Erro ao processar dados gerais de compras: {e}")
                    st.exception(e)
    
    
    # --- Bloco de Anotações Único para toda a Aba ---
    st.subheader("📝 Bloco de notas")
    # Carrega anotações salvas
    anotacoes = utils.carregar_anotacoes()
    # Cria o text_area com opção de salvar
    nova_anotacao = st.text_area(
        "(Salva automaticamente ao modificar)",
        value=anotacoes,
        height=150,
        key="anotacoes_compras"
        )
    # Salva automaticamente quando houver alteração
    if nova_anotacao != anotacoes:
        if utils.salvar_anotacoes(nova_anotacao):
            st.toast("Salvo", icon="✅")



######################################################################################



#=======================================================================
# ABA 2: CONTROLADOS
#=======================================================================
with tab_map["controlados"]:
    # Carrega os dados usando a função do database.py (já aplica filtros globais de marca/produto)
    df_controlados: pd.DataFrame = db.load_controlados_data(
        data_inicio_selecionada, data_fim_query,
        marca_selecionada, produto_nome_filtro
        )
    # Exibe os dados se o DataFrame não estiver vazio
    if not df_controlados.empty:
        # Métrica simples
        try:
            st.metric("Total de Vendas", utils.formatar_inteiro(len(df_controlados)))
        except Exception as e:
            st.error(f"Erro ao calcular métrica de Controlados: {e}")
        # Exibe a tabela
        st.dataframe(
            df_controlados,
            use_container_width=True,
            hide_index=True,
            column_config={ # Formata a coluna de data e ajusta títulos
                C.COL_DATA: st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                C.COL_VENDEDOR: st.column_config.TextColumn("Vendedor"),
                C.COL_NOME_MEDICAMENTO: st.column_config.TextColumn("Nome do Medicamento", width="large"),
                C.COL_QTD_VENDIDA: st.column_config.TextColumn("Quantidade Vendida"),
                C.COL_LOTE: st.column_config.TextColumn("Lote"),
                C.COL_VENDA: st.column_config.NumberColumn("Venda", format="%d"),
                C.COL_NFE: st.column_config.TextColumn("NFe"),
                C.COL_CLIENTE: st.column_config.TextColumn("Cliente", width="medium"),
                C.COL_ENDERECO: st.column_config.TextColumn("Endereço", width="large"),
                C.COL_CNPJ: st.column_config.TextColumn("CNPJ"),
                C.COL_CPF: st.column_config.TextColumn("CPF"),
                C.COL_DOC: st.column_config.TextColumn("DOC"),
                },
            # Ordem das colunas
            column_order=(
                C.COL_DATA, C.COL_VENDEDOR, C.COL_NOME_MEDICAMENTO, C.COL_QTD_VENDIDA, C.COL_LOTE,
                C.COL_VENDA, C.COL_NFE, C.COL_CLIENTE, C.COL_ENDERECO, C.COL_CNPJ, C.COL_CPF, C.COL_DOC
                )
            )
        # Botão de Download
        utils.gerar_botao_download(df_controlados, "relatorio_controlados", key_suffix="_ctrl")
    else:
        st.info(C.TEXTO_NENHUM_DADO)



######################################################################################



#=======================================================================
# ABA 3: CLIENTES
#=======================================================================

# ABA CLIENTES
with tab_map["clientes"]:
    # Abas internas 
    clientes_geral, stanley = st.tabs(["😁 CLIENTES", "🪮 STANLEY"])
    
    # SUB-ABA CLIENTES GERAL
    with clientes_geral:
        clientes_ultima_compra, construcao321 = st.tabs(["ÚLTIMA COMPRA", "🚧 EM OBRAS"])
        
        with clientes_ultima_compra:        
            # --- Filtros ---
            col_fcli1, col_fcli2 = st.columns(2)
            with col_fcli1:
                cliente_filtro_uc = st.text_input(
                    "Nome do Cliente",
                    key="uc_cliente_input",
                    help="Digite parte do nome do cliente para filtrar."
                )
                # `marcas_list` deve estar disponível (carregada na sidebar)
                marca_filtro_uc = st.selectbox(
                    "Marca",
                    options=marcas_list, # Usa lista global
                    index=0, # Padrão "Todas"
                    key="uc_marca_select",
                    help="Filtrar clientes que compraram produtos desta marca."
                )
                
            with col_fcli2:
                produto_filtro_uc = st.text_input(
                    "Nome do Produto",
                    key="uc_produto_input",
                    help="Digite parte do nome de um produto para filtrar clientes que o compraram."
                )

            # --- Carregar e Exibir Dados ---
            df_ultima_compra = db.load_ultima_compra_cliente_data(
                cliente_filtro=cliente_filtro_uc.strip() if cliente_filtro_uc.strip() else None,
                marca_filtro=marca_filtro_uc if marca_filtro_uc != "Todas" else None,
                produto_filtro=produto_filtro_uc.strip() if produto_filtro_uc.strip() else None
            )
            
            if not df_ultima_compra.empty:
                st.dataframe(
                    df_ultima_compra,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        C.COL_ULT_COMPRA_DATA: st.column_config.DateColumn(
                            "Última Compra",
                            format="DD/MM/YYYY"
                        ),
                        C.COL_ULT_COMPRA_CLIENTE: st.column_config.TextColumn(
                            "Cliente",
                            width="large"
                        )
                    },
                    
                    column_order=(C.COL_ULT_COMPRA_DATA, "Código", C.COL_ULT_COMPRA_CLIENTE,
                                "CNPJ","CPF","FONECOM","FONERES","FONEFAX","FONECEL","FONESAC")
                )
                utils.gerar_botao_download(
                    df_ultima_compra,
                    "ultima_compra_clientes",
                    key_suffix="_uc"
                )
            else:
                st.info("Nenhum cliente encontrado com os filtros selecionados.")



    # STANLEY
    with stanley:
        
        # Abas internas para Vendas (NF), Produtos e Unidades
        stanley_data_ultima_compra, stanley_vendas_tab, stanley_produtos_tab, stanley_unidades_tab, stanley_faturamento_por_unidade, stanley_faturamento_historico = st.tabs(['ÚLTIMA COMPRA', 'VENDAS', 'PRODUTOS', 'UNIDADES','FATURAMENTO', 'HISTÓRICO'])
        
        with stanley_data_ultima_compra:
            
            # --- Carregar e Exibir Dados ---
            df_ultima_compra_stanley = db.load_ultima_compra_cliente_data_stanley(
                cliente_filtro=cliente_filtro_uc.strip() if cliente_filtro_uc.strip() else None,
                marca_filtro=marca_filtro_uc if marca_filtro_uc != "Todas" else None,
                produto_filtro=produto_filtro_uc.strip() if produto_filtro_uc.strip() else None
            )
            if not df_ultima_compra_stanley.empty:
                st.dataframe(
                    df_ultima_compra_stanley,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        C.COL_ULT_COMPRA_DATA: st.column_config.DateColumn(
                            "Última Compra",
                            format="DD/MM/YYYY"
                        ),
                        C.COL_ULT_COMPRA_CLIENTE: st.column_config.TextColumn(
                            "Cliente",
                            width="large"
                        )
                    },
                    
                    column_order=(C.COL_ULT_COMPRA_DATA, "Código", C.COL_ULT_COMPRA_CLIENTE,
                                "CNPJ","FONECOM","FONERES","FONEFAX","FONECEL","FONESAC")
                )
                utils.gerar_botao_download(
                    df_ultima_compra_stanley,
                    "ultima_compra_clientes_stanley",
                    key_suffix="_uc"
                )
            else:
                st.info("Nenhum cliente encontrado com os filtros selecionados.")
        
        
        # --- Sub-Aba: Stanley Vendas (Notas Fiscais) ---
        with stanley_vendas_tab:
            # Carrega dados das vendas/NFs para Stanley (aplica filtros globais de marca/produto)
            df_stanley_vendas: pd.DataFrame = db.load_stanley_vendas_data(
                data_inicio_selecionada, data_fim_query,
                marca_selecionada, produto_nome_filtro
                )
            if not df_stanley_vendas.empty:
                # Métricas
                try:
                    metricas_stv: Dict[str, str] = {
                        "Total de Notas Fiscais": utils.formatar_inteiro(len(df_stanley_vendas)),
                        "Valor Total das Notas": utils.formatar_moeda(df_stanley_vendas[C.COL_TOTAL_NOTA].sum())
                        }
                    cols_stv = st.columns(len(metricas_stv))
                    exibir_metricas(cols_stv, metricas_stv)
                except KeyError as e:
                    st.error(f"Erro ao calcular métricas Stanley (Vendas): Coluna '{e}' não encontrada.")
                except Exception as e:
                    st.error(f"Erro inesperado ao calcular métricas Stanley (Vendas): {e}")
                
                # Tabela
                st.dataframe(
                    df_stanley_vendas,
                    use_container_width=True,
                    hide_index=True,
                    column_config={ # Títulos e formatos
                        C.COL_CIDADE: st.column_config.TextColumn("Cidade"),
                        C.COL_UNIDADE_STANLEY: st.column_config.TextColumn("Unidade", width="medium"),
                        C.COL_PEDIDO_COMPRA: st.column_config.TextColumn("Pedido de Compra", width="small"),
                        C.COL_NF: st.column_config.TextColumn("NF"),
                        C.COL_VALOR_PRODUTOS: st.column_config.NumberColumn("Valor Produtos", format="R$ %.2f"),
                        C.COL_FRETE: st.column_config.NumberColumn("Frete", format="R$ %.2f"),
                        C.COL_TOTAL_NOTA: st.column_config.NumberColumn("Total da Nota", format="R$ %.2f"),
                        C.COL_CUSTO_TOTAL: st.column_config.NumberColumn("Custo Total", format="R$ %.2f"),
                        C.COL_LUCRO: st.column_config.NumberColumn("Lucro", format="R$ %.2f"),
                        C.COL_MARGEM: st.column_config.NumberColumn("Margem", format="%.0f %%"),
                        C.COL_TRANSPORTADORA: st.column_config.TextColumn("Transportadora", width="medium"),
                        C.COL_DATA: st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        C.COL_VENDEDOR: st.column_config.TextColumn("Vendedor", width="medium"),
                        C.COL_CHAVE_ACESSO: st.column_config.TextColumn("Chave de Acesso", width="large", help="Chave de Acesso da Nota Fiscal Eletrônica"),
                        C.COL_OBSERVACOES_NOTA: st.column_config.TextColumn("Observações da Nota", width="large"),
                        },
                    
                    # Ordem das colunas
                    column_order=(
                        C.COL_DATA, C.COL_CIDADE, C.COL_UNIDADE_STANLEY, C.COL_PEDIDO_COMPRA, C.COL_NF,
                        C.COL_VALOR_PRODUTOS, C.COL_FRETE, C.COL_TOTAL_NOTA, C.COL_CUSTO_TOTAL, C.COL_LUCRO, C.COL_MARGEM, C.COL_TRANSPORTADORA,
                        C.COL_VENDEDOR, C.COL_CHAVE_ACESSO, C.COL_OBSERVACOES_NOTA
                        )
                    )
                
                # Botão de Download
                utils.gerar_botao_download(df_stanley_vendas, "stanley_notas_fiscais", key_suffix="_stv")
            else:
                st.info(C.TEXTO_NENHUM_DADO)
                
        # --- Sub-Aba: Stanley Produtos ---
        with stanley_produtos_tab:
            # Filtros específicos para esta sub-aba 
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                vendedor_stanley: str = st.text_input("Filtrar por Vendedor", "", key="stanley_vendedor_input", help="Filtrar por nome do vendedor")
                produto_stanley: str = st.text_input("Filtrar por Produto", "", key="stanley_produto_input", help="Filtrar por nome do produto vendido")
            with col_f2:
                unidade_stanley: str = st.text_input("Filtrar por Unidade", "", key="stanley_unidade_input", help="Filtrar por nome da unidade/cliente Stanley")
                codigo_produto_stanley: str = st.text_input("Código do Produto", "", key="stanley_codigo_input", help="Filtrar por código exato do produto")
            # Carrega dados dos produtos vendidos para Stanley com filtros específicos
            # NÃO usa filtros globais da sidebar aqui (exceto datas), apenas os locais desta aba
            df_stanley_produtos: pd.DataFrame = db.load_stanley_produtos_data(
                data_inicio_selecionada, data_fim_query,
                vendedor_stanley or None, # Passa None se string vazia
                produto_stanley or None,
                unidade_stanley or None,
                codigo_produto_stanley or None
                )
            if not df_stanley_produtos.empty:
                # Métricas 
                try:
                    total_vendas_stp = len(df_stanley_produtos[C.COL_VENDA].unique())
                    # Usa .sum() em colunas que podem conter NaN após conversão para float
                    total_produtos_stp = df_stanley_produtos[C.COL_QUANTIDADE].sum()
                    valor_total_stp = df_stanley_produtos[C.COL_TOTAL_VENDA].sum()
                    metricas_stp: Dict[str, str] = {
                        "Total de Vendas": utils.formatar_inteiro(total_vendas_stp),
                        "Produtos Vendidos": utils.formatar_inteiro(total_produtos_stp),
                        "Valor Total": utils.formatar_moeda(valor_total_stp)
                        }
                    cols_stp = st.columns(len(metricas_stp))
                    exibir_metricas(cols_stp, metricas_stp)
                except KeyError as e:
                    st.error(f"Erro ao calcular métricas Stanley (Produtos): Coluna '{e}' não encontrada.")
                except Exception as e:
                    st.error(f"Erro inesperado ao calcular métricas Stanley (Produtos): {e}")
                # Tabela
                st.dataframe(
                    df_stanley_produtos,
                    use_container_width=True,
                    hide_index=True,
                    column_config={ # Títulos e formatos
                        C.COL_DATA: st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        C.COL_VENDEDOR: st.column_config.TextColumn("Vendedor", width="medium"),
                        C.COL_VENDA: st.column_config.NumberColumn("Venda", format="%d"),
                        C.COL_NF: st.column_config.TextColumn("NF"),
                        C.COL_UNIDADE_STANLEY: st.column_config.TextColumn("Unidade", width="medium"),
                        C.COL_COMPRA_STANLEY: st.column_config.TextColumn("Compra", width="small"), # Pedido de Compra
                        C.COL_CODIGO: st.column_config.TextColumn("Código"), # Código do Produto
                        C.COL_PRODUTO: st.column_config.TextColumn("Produto", width="large"),
                        C.COL_QUANTIDADE: st.column_config.NumberColumn("Quantidade", format="%.0f"), # Inteiro
                        C.COL_CUSTO_UNITARIO: st.column_config.NumberColumn("Custo Unitário", format="R$ %.2f"),
                        C.COL_PRECO_UNITARIO: st.column_config.NumberColumn("Preço Unitário", format="R$ %.2f"),
                        C.COL_MARGEM: st.column_config.NumberColumn("Margem", format="%.0f%%", help="Margem de Lucro Bruta sobre o Custo"), # Percentual inteiro
                        C.COL_TOTAL_VENDA: st.column_config.NumberColumn("Total Venda", format="R$ %.2f"), # Total do Item
                        },
                    # Ordem das colunas
                    column_order=(
                        C.COL_DATA, C.COL_VENDEDOR, C.COL_VENDA, C.COL_NF, C.COL_UNIDADE_STANLEY, C.COL_COMPRA_STANLEY,
                        C.COL_CODIGO, C.COL_PRODUTO, C.COL_QUANTIDADE, C.COL_CUSTO_UNITARIO,
                        C.COL_PRECO_UNITARIO, C.COL_MARGEM, C.COL_TOTAL_VENDA
                        )
                    )
                # Botão de Download
                utils.gerar_botao_download(df_stanley_produtos, "stanley_produtos_vendidos", key_suffix="_stp")
            else:
                st.info(C.TEXTO_NENHUM_DADO)



        # --- Sub-Aba: Stanley Unidades ---
        with stanley_unidades_tab:
            # Carrega os dados (não precisa de filtros)
            df_stanley_unidades = db.load_stanley_unidades_data()
            
            num_unidades = len(df_stanley_unidades) # ou df_stanley_unidades.shape[0]
            st.metric(label="Número de Unidades Stanley Ativas", value=num_unidades)
            
            if not df_stanley_unidades.empty:
                st.dataframe(
                    df_stanley_unidades,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        C.COL_ST_UNIDADE_NOME: st.column_config.TextColumn(
                            "Unidade Stanley",
                            width="large"
                        ),
                        C.COL_ST_UNIDADE_CIDADE: st.column_config.TextColumn(
                            "Cidade"
                        ),
                        C.COL_ST_UNIDADE_UF: st.column_config.TextColumn(
                            "UF",
                            width="small"
                        )
                    },
                    # A ordem já vem do SELECT/rename na função DB
                    column_order=(C.COL_ST_UNIDADE_NOME, C.COL_ST_UNIDADE_CIDADE, C.COL_ST_UNIDADE_UF)
                )
                utils.gerar_botao_download(
                    df_stanley_unidades,
                    "lista_unidades_stanley",
                    key_suffix="_stu"
                )
            else:
                st.info("Nenhuma unidade Stanley ativa encontrada.")



        with stanley_faturamento_por_unidade:
            # Os filtros de data são passados automaticamente da sidebar global
            df_faturamento_unidade = db.load_stanley_faturamento_por_unidade_data(
                data_inicio_selecionada, data_fim_query
            )
            if not df_faturamento_unidade.empty:
                # Calcula as métricas de somatório total
                total_faturamento = df_faturamento_unidade[C.COL_FATURAMENTO_PRODUTOS].sum()
                total_custo = df_faturamento_unidade[C.COL_CUSTO_TOTAL].sum()
                total_lucro = df_faturamento_unidade[C.COL_LUCRO].sum()
                margem_total_perc = ((total_faturamento / total_custo) - 1) * 100 if total_custo != 0 else 0.0
                # Exibe as métricas de somatório
                metricas_faturamento_unidade: Dict[str, str] = {
                    "Faturamento Total": utils.formatar_moeda(total_faturamento),
                    "Custo Total": utils.formatar_moeda(total_custo),
                    "Lucro Total": utils.formatar_moeda(total_lucro),
                    "Margem Total": utils.formatar_percentual(margem_total_perc, casas_decimais=0)
                }
                cols_metrics_fu = st.columns(len(metricas_faturamento_unidade))
                exibir_metricas(cols_metrics_fu, metricas_faturamento_unidade)
                
                st.markdown("---") # Adiciona uma linha divisória para separar as métricas da tabela
                
                # Exibe o DataFrame com os dados detalhados por unidade
                st.dataframe(
                    df_faturamento_unidade,
                    use_container_width=True, # Ocupa toda a largura disponível
                    hide_index=True,          # Oculta o índice do Pandas
                    column_config={           # Configurações de exibição para cada coluna
                        C.COL_UNIDADE_STANLEY: st.column_config.TextColumn("Unidade"), # Título "Unidade" para a coluna
                        C.COL_FATURAMENTO_PRODUTOS: st.column_config.NumberColumn("Faturamento em Produtos", format="R$ %.2f"),
                        C.COL_CUSTO_TOTAL: st.column_config.NumberColumn("Custo Total", format="R$ %.2f"),
                        C.COL_LUCRO: st.column_config.NumberColumn("Lucro", format="R$ %.2f"),
                        C.COL_MARGEM: st.column_config.NumberColumn("Margem", format="%.0f %%"), # Formata como percentual inteiro
                    },
                    # Define a ordem das colunas para exibição na tabela
                    column_order=(
                        C.COL_UNIDADE_STANLEY,
                        C.COL_FATURAMENTO_PRODUTOS,
                        C.COL_CUSTO_TOTAL,
                        C.COL_LUCRO,
                        C.COL_MARGEM
                    )
                )
                # Adiciona o botão de download para a tabela de faturamento por unidade
                utils.gerar_botao_download(
                    df_faturamento_unidade,
                    "stanley_faturamento_por_unidade", # Nome base do arquivo para download
                    key_suffix="_stfu" # Sufixo único para a chave do botão
                )
            else:
                # Mensagem exibida se não houver dados após a consulta
                st.info(C.TEXTO_NENHUM_DADO)



        with stanley_faturamento_historico:
            df_faturamento_stanley = db.get_faturamento_historico_stanley()
            if not df_faturamento_stanley.empty:
                # Exibir DataFrame
                st.dataframe(
                    df_faturamento_stanley,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        C.COL_SF_ANO: st.column_config.NumberColumn("Ano", format="%d"),
                        C.COL_SF_MES: st.column_config.NumberColumn("Mês", format="%d"),
                        C.COL_SF_FATURAMENTO_PRODUTOS: st.column_config.NumberColumn(
                            "Faturamento", format="R$ %.2f"),
                        C.COL_SF_CUSTO_TOTAL: st.column_config.NumberColumn(
                            "Custo Total", format="R$ %.2f"),
                        C.COL_SF_LUCRO: st.column_config.NumberColumn(
                            "Lucro", format="R$ %.2f"),
                        C.COL_SF_MARGEM: st.column_config.NumberColumn(
                            "Margem (%)", format="%d %%"), # Formata como porcentagem
                    }
                )
                
                # --- Botão de Download ---
                utils.gerar_botao_download(
                    df_faturamento_stanley,
                    "faturamento_historico_stanley",
                    key_suffix="_stanley_faturamento"
                )
            else:
                st.info(C.TEXTO_IS_FILTRO_SEM_RESULTADOS) # Reutilizando a constante de "sem resultados"



######################################################################################



#=======================================================================
# ABA 4: ORÇAMENTO
#=======================================================================
with tab_map["orcamento"]:
    orcamento_margem, orcamento_estoque , orcamento_comparador = st.tabs(['MARGEM', 'ESTOQUE', 'COMPARADOR'])
    
    # ORÇAMENTO MARGEM
    with orcamento_margem:
        # Input para o código do orçamento
        codigo_orcamento_input: int = st.number_input(
            "Código de Orçamento", # Label
            min_value=0, # Permite 0 como valor inicial/padrão
            value=0,     # Valor padrão 0
            step=1,      # Incremento de 1
            key="orcamento_input", # Chave única
            help="Insira o número do orçamento que deseja consultar."
            )
        # Processa apenas se um código válido (>0) for inserido
        if codigo_orcamento_input > 0:
            # Carrega dados do orçamento (produtos e totais)
            # Spinners são mostrados pelas funções load_*
            df_orc_produtos: pd.DataFrame = db.load_orcamento_produtos_data(codigo_orcamento_input)
            df_orc_totais: Optional[pd.DataFrame] = db.load_orcamento_totais_data(codigo_orcamento_input) # Retorna None se não achar
            # Verifica se os dados foram carregados com sucesso
            if df_orc_totais is None or df_orc_totais.empty:
                st.warning(C.TEXTO_ORCAMENTO_NAO_ENCONTRADO.format(codigo=codigo_orcamento_input))
            elif df_orc_produtos.empty:
                # Pode acontecer se a venda existe mas não tem itens válidos (ex: modo='R')
                st.warning(f"Orçamento {codigo_orcamento_input} encontrado, mas não contém itens válidos ou ocorreu um erro ao carregar os itens.")
            else:
                # --- Cálculos e Exibição ---
                try:
                    # Extrai os totais da venda (DataFrame de uma linha)
                    totais = df_orc_totais.iloc[0]
                    valor_final_orc = totais[C.COL_VALOR_FINAL]
                    # Calcula o custo total dos produtos no orçamento
                    total_custo_orc = df_orc_produtos[C.COL_CUSTO_TOTAL].sum()
                    # Calcula a margem total
                    # Trata divisão por zero
                    margem_total_perc = ((valor_final_orc / total_custo_orc) - 1) * 100 if total_custo_orc != 0 else 0.0
                    # Exibe as métricas do orçamento
                    metricas_orc: Dict[str, str] = {
                        "Quantidade de Produtos": utils.formatar_inteiro(len(df_orc_produtos)),
                        "Custo Total": utils.formatar_moeda(total_custo_orc),
                        "Valor em Produtos": utils.formatar_moeda(totais[C.COL_VALOR_EM_PRODUTOS]),
                        "Desconto Geral": utils.formatar_moeda(totais[C.COL_DESCONTO]),
                        "Valor Final": utils.formatar_moeda(valor_final_orc),
                        "Margem Total": utils.formatar_percentual(margem_total_perc, casas_decimais=0) # Percentual inteiro
                        }
                    # Colunas
                    cols_orc = st.columns(len(metricas_orc))
                    exibir_metricas(cols_orc, metricas_orc)
                    st.divider() # Linha divisória
                    # Exibe a tabela de produtos do orçamento
                    st.dataframe(
                        df_orc_produtos,
                        use_container_width=True,
                        hide_index=True,
                        column_config={ # Títulos e formatos
                            C.COL_CODIGO: st.column_config.TextColumn("Código"),
                            C.COL_PRODUTO: st.column_config.TextColumn("Produto", width="large"),
                            C.COL_QUANTIDADE: st.column_config.NumberColumn("Quantidade", format="%.0f"), # Inteiro
                            C.COL_CUSTO_UNITARIO: st.column_config.NumberColumn("Custo Unitário", format="R$ %.2f"),
                            C.COL_PRECO_UNITARIO: st.column_config.NumberColumn("Preço Unitário", format="R$ %.2f"),
                            C.COL_CUSTO_TOTAL: st.column_config.NumberColumn("Custo Total", format="R$ %.2f"),
                            C.COL_PRECO_TOTAL: st.column_config.NumberColumn("Preço Total", format="R$ %.2f"),
                            C.COL_MARGEM: st.column_config.NumberColumn("Margem", format="%.0f%%"), # Percentual inteiro
                            },
                        # Ordem das colunas
                        column_order = (
                            C.COL_CODIGO, C.COL_PRODUTO, C.COL_QUANTIDADE, C.COL_CUSTO_UNITARIO,
                            C.COL_PRECO_UNITARIO, C.COL_CUSTO_TOTAL, C.COL_PRECO_TOTAL, C.COL_MARGEM
                            )
                        )
                    # Botão de Download para os itens
                    utils.gerar_botao_download(df_orc_produtos, f"orcamento_{codigo_orcamento_input}_itens", key_suffix="_orc")
                except KeyError as e:
                    st.error(f"Erro ao processar dados do orçamento {codigo_orcamento_input}: Coluna '{e}' não encontrada.")
                except Exception as e:
                    st.error(f"Erro inesperado ao processar orçamento {codigo_orcamento_input}: {e}")
                    st.exception(e)
        elif codigo_orcamento_input == 0: # Só mostra a mensagem inicial se for 0
            # Mensagem inicial se nenhum código foi inserido
            st.info(C.TEXTO_DIGITE_CODIGO_ORCAMENTO)
        # Se for None ou outro tipo inválido, number_input deve tratar ou retornar 0
    
    
    
    # ORÇAMENTO ESTOQUE
    with orcamento_estoque:
        # 1. Entrada de texto para códigos de orçamento
        orcamento_input = st.text_input(
            "Insira os códigos dos orçamentos (separados por vírgula):",
            key="orcamento_stanley_input",
            placeholder="Ex: 36090, 53861, 123456"
        )
        codigos_orcamento: List[int] = []
        if orcamento_input:
            # Remover espaços e dividir por vírgula
            codigos_str = [c.strip() for c in orcamento_input.split(',') if c.strip()]
            # Converter para inteiros, ignorando entradas não numéricas
            for cod_str in codigos_str:
                if cod_str.isdigit(): # Verifica se a string contém apenas dígitos
                    codigos_orcamento.append(int(cod_str))
                else:
                    st.warning(f"O valor '{cod_str}' não é um código de orçamento válido e será ignorado.")
        # 2. Botão para carregar os dados
        if st.button("Analisar Orçamentos", key="btn_analisar_orcamento"):
            if codigos_orcamento:
                df_orcamento_estoque = db.get_orcamento_estoque(codigos_orcamento)
                if not df_orcamento_estoque.empty:
                    st.markdown("---")
                    st.dataframe(
                        df_orcamento_estoque,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            C.COL_CODIGO_BR: st.column_config.TextColumn("Código"),
                            C.COL_PRODUTO: st.column_config.TextColumn("Produto"),
                            C.COL_MARCA: st.column_config.TextColumn("Marca"),
                            C.COL_QUANTIDADE: st.column_config.NumberColumn("Quantidade", format="%d"),
                            C.COL_ESTOQUE_BR: st.column_config.NumberColumn("Estoque", format="%d"),
                            C.COL_DIFERENCA: st.column_config.NumberColumn("Diferença", format="%d"),
                        }
                    )
                    # Botão de Download para os dados filtrados
                    utils.gerar_botao_download(
                        df_orcamento_estoque,
                        "relatorio_orcamento_estoque",
                        key_suffix="_orcamento_estoque"
                    )
                else:
                    st.info("Nenhum dado encontrado para os códigos de orçamento informados ou filtros aplicados.")
            else:
                st.warning("Por favor, insira pelo menos um código de orçamento para analisar.")
    
    # COMPARADOR ORÇAMENTO / VENDA
    with orcamento_comparador:
        col_inicial, col_final = st.columns(2)
        with col_inicial:
            codigo_inicial = st.number_input(
                "Código Inicial",
                min_value=0,
                value=0,
                step=1,
                key="comp_orc_inicial_input",
                help="Insira o código do primeiro orçamento para comparação."
            )
        with col_final:
            codigo_final = st.number_input(
                "Código Final",
                min_value=0,
                value=0,
                step=1,
                key="comp_orc_final_input",
                help="Insira o código do segundo orçamento para comparação."
            )
            
        if st.button("Comparar Orçamentos", key="btn_comparar_orcamentos"):
            if codigo_inicial > 0 and codigo_final > 0:
                df_comparacao = db.compare_orcamentos(codigo_inicial, codigo_final)

                if not df_comparacao.empty:
                    st.dataframe(
                        df_comparacao,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            C.COL_CODIGO_BR: st.column_config.NumberColumn("Cód. BR", format="%d"),
                            C.COL_PRODUTO: st.column_config.TextColumn("Produto", width="large"),
                            "Inicial": st.column_config.NumberColumn(codigo_inicial, format="%d"),
                            "Final": st.column_config.NumberColumn(codigo_final, format="%d"),
                            C.COL_DIFERENCA: st.column_config.NumberColumn(f"Diferença ({codigo_inicial} - {codigo_final})", format="%d"),
                        }
                    )
                    utils.gerar_botao_download(
                        df_comparacao,
                        f"comparacao_orcamentos_{codigo_inicial}_vs_{codigo_final}",
                        key_suffix="_comp_orc"
                    )
                else:
                    st.info("Nenhum dado encontrado para os orçamentos informados ou eles não contêm produtos em comum.")
            else:
                st.warning("Por favor, insira códigos de orçamento válidos para ambos os campos.")












######################################################################################



#=======================================================================
# ABA 5: LIGEIRINHO (FRETE)
#=======================================================================
with tab_map["ligeirinho"]:
    # Carrega dados de frete (já aplica filtro de data)
    df_frete: pd.DataFrame = db.load_ligeirinho_frete_data(data_inicio_selecionada, data_fim_query)
    valor_inicial = utils.carregar_ajuste()
    ajuste_do_frete, q,w,e,r = st.columns(5)
    with ajuste_do_frete:
        # Cria o input numérico
        novo_valor = st.number_input(
            "Digite o valor de ajuste:",
            value=valor_inicial,
            format="%.2f"
            )
        # Salva automaticamente quando o valor é alterado
        if novo_valor != valor_inicial:
            utils.salvar_ajuste(novo_valor)
            st.success("Valor salvo com sucesso!")
    if not df_frete.empty:
        # Métricas
        try:
            metricas_frt: Dict[str, str] = {
                "Total de Vendas com Frete" : utils.formatar_inteiro(len(df_frete)),
                "Valor Total de Fretes" : utils.formatar_moeda(df_frete[C.COL_VALOR_FRETE].sum()),
                "Ajuste" : f"{utils.formatar_moeda(valor_inicial)}",
                "Total c/ Ajuste" : f"{utils.formatar_moeda(df_frete[C.COL_VALOR_FRETE].sum() + valor_inicial)}"
            }
            cols_frt = st.columns(len(metricas_frt)) # Usa 2 colunas agora
            exibir_metricas(cols_frt, metricas_frt)
        except KeyError as e:
            st.error(f"Erro ao calcular métricas de Frete: Coluna '{e}' não encontrada.")
        except Exception as e:
            st.error(f"Erro inesperado ao calcular métricas de Frete: {e}")
        # Tabela
        st.dataframe(
            df_frete,
            use_container_width=True,
            hide_index=True,
            column_config={ # Títulos e formatos
                C.COL_DATA_HORA: st.column_config.DatetimeColumn("Data e Hora", format="DD/MM/YYYY HH:mm"),
                C.COL_VENDA: st.column_config.NumberColumn("Venda", format="%d"),
                C.COL_VENDEDOR: st.column_config.TextColumn("Vendedor", width="medium"),
                C.COL_VALOR_PRODUTOS: st.column_config.NumberColumn("Valor Produtos", format="R$ %.2f"),
                C.COL_TRANSPORTADORA: st.column_config.TextColumn("Transportadora", help="Nome da transportadora registrada na venda"),
                C.COL_VALOR_FRETE: st.column_config.NumberColumn("Valor Frete", format="R$ %.2f"),
                C.COL_CLIENTE: st.column_config.TextColumn("Cliente", width="medium"),
                },
            # Ordem das colunas 
            column_order=(
                C.COL_DATA_HORA, C.COL_VENDA, C.COL_VENDEDOR, C.COL_VALOR_PRODUTOS,
                C.COL_TRANSPORTADORA, C.COL_VALOR_FRETE, C.COL_CLIENTE
                )
            )
        # Botão de Download
        utils.gerar_botao_download(df_frete, "relatorio_fretes", key_suffix="_frt")
    else:
        # Mensagem se não houver dados
        st.info("Nenhum registro de frete encontrado para o período selecionado com valor > 0.")



######################################################################################



#=======================================================================
# ABA 6: PRODUTOS
#=======================================================================
with tab_map["produtos"]:
    # Abas internas para Vendas e Custo x Estoque
    vendas_prod_tab, entradas_tab, vencimento_tab, custoestoque_tab = st.tabs(['VENDAS', 'ENTRADAS', 'VENCIMENTO','CUSTO*ESTOQUE'])
    
    # --- Sub-Aba: Detalhes de Vendas ---
    with vendas_prod_tab:
        # Filtros adicionais específicos para esta sub-aba
        st.markdown("**Filtros Adicionais (Vendas de Produtos):**")
        col_fp1, col_fp2 = st.columns(2)
        with col_fp1:
            # Input para código da venda (0 para ignorar)
            codigo_venda_prod: int = st.number_input("Código da Venda", 0, step=1, key="prod_venda_input_tab6", help="Filtrar por um código de venda específico (0 = todos).")
            vendedor_filtro_prod: str = st.text_input("Filtrar por Vendedor", "", key="prod_vendedor_input_tab6", help="Filtrar por nome do vendedor.")
        with col_fp2:
            # Input para código do produto (texto, busca exata)
            codigo_produto_prod: str = st.text_input("Código do Produto", "", key="prod_codigo_input_tab6", help="Filtrar por código exato do produto.")
            cliente_filtro_prod: str = st.text_input("Filtrar por Cliente", "", key="prod_cliente_input_tab6", help="Filtrar por nome do cliente.")
        # Carrega dados detalhados das vendas, aplicando filtros locais e globais
        df_produtos_vendas: pd.DataFrame = db.load_produtos_vendas_data(
            data_inicio_selecionada, data_fim_query,
            codigo_venda_prod if codigo_venda_prod > 0 else None, # Passa None se for 0
            vendedor_filtro_prod or None,
            cliente_filtro_prod or None,
            codigo_produto_prod or None,
            marca_selecionada, # Usa filtro global de marca
            produto_nome_filtro # Usa filtro global de nome de produto
            )
        if not df_produtos_vendas.empty:
            # Métricas
            try:
                total_vendas_prdv = len(df_produtos_vendas[C.COL_VENDA].unique())
                total_produtos_prdv = df_produtos_vendas[C.COL_QUANTIDADE].sum()
                valor_total_prdv = df_produtos_vendas[C.COL_PRECO_TOTAL].sum()
                metricas_prdv: Dict[str, str] = {
                    "Total de Vendas": utils.formatar_inteiro(total_vendas_prdv),
                    "Total de Produtos Vendidos": utils.formatar_inteiro(total_produtos_prdv),
                    "Valor Total": utils.formatar_moeda(valor_total_prdv)
                }
                cols_prdv = st.columns(len(metricas_prdv))
                exibir_metricas(cols_prdv, metricas_prdv)
            except KeyError as e:
                st.error(f"Erro ao calcular métricas de Vendas de Produtos: Coluna '{e}' não encontrada.")
            except Exception as e:
                st.error(f"Erro inesperado ao calcular métricas de Vendas de Produtos: {e}")
            # Tabela
            st.dataframe(
                df_produtos_vendas,
                use_container_width=True,
                hide_index=True,
                column_config={ # Títulos e formatos
                    C.COL_DATA: st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY HH:mm"), # Usa Datetime aqui
                    C.COL_VENDEDOR: st.column_config.TextColumn("Vendedor", width="medium"),
                    C.COL_VENDA: st.column_config.NumberColumn("Venda", format="%d"),
                    C.COL_CLIENTE: st.column_config.TextColumn("Cliente", width="medium"),
                    C.COL_CODIGO: st.column_config.TextColumn("Código"), # Código do produto
                    C.COL_PRODUTO: st.column_config.TextColumn("Produto", width="large"),
                    C.COL_MARCA: st.column_config.TextColumn("Marca"),
                    C.COL_QUANTIDADE: st.column_config.NumberColumn("Quantidade", format="%.0f"), # Inteiro
                    C.COL_CUSTO_UNITARIO: st.column_config.NumberColumn("Custo Unitário", format="R$ %.2f"),
                    C.COL_PRECO_UNITARIO: st.column_config.NumberColumn("Preço Unitário", format="R$ %.2f"),
                    C.COL_MARGEM: st.column_config.NumberColumn("Margem", format="%.0f%%"), # Percentual inteiro
                    C.COL_PRECO_TOTAL: st.column_config.NumberColumn("Preço Total", format="R$ %.2f"),
                    },
                # Ordem das colunas 
                column_order=(
                    C.COL_DATA, C.COL_VENDEDOR, C.COL_VENDA, C.COL_CLIENTE, C.COL_CODIGO,
                    C.COL_PRODUTO, C.COL_MARCA, C.COL_QUANTIDADE, C.COL_CUSTO_UNITARIO,
                    C.COL_PRECO_UNITARIO, C.COL_MARGEM, C.COL_PRECO_TOTAL
                    )
                )
            # Botão de Download
            utils.gerar_botao_download(df_produtos_vendas, "detalhe_vendas_produtos", key_suffix="_prdv")
        else:
            # Mensagem se não houver dados
            st.info("Nenhuma venda encontrada com os filtros selecionados.")




    # --- Sub-Aba: Entradas ---
    with entradas_tab:
        # --- Filtros para Entradas ---
        st.markdown("**Filtros para Entradas:**")
        col_f_ent_data1, col_f_ent_data2 = st.columns(2)
        with col_f_ent_data1:
            data_inicio_entradas_local = st.date_input(
                "Data Inicial para Entradas",
                value=data_inicio_selecionada, # Padrão baseado no global
                min_value=date(2000, 1, 1),
                max_value=data_hoje,
                key="entradas_data_ini_local",
                format="DD/MM/YYYY"
            )
        with col_f_ent_data2:
            data_fim_entradas_local = st.date_input(
                "Data Final para Entradas",
                value=data_fim_selecionada, # Padrão baseado no global
                min_value=data_inicio_entradas_local,
                max_value=data_hoje,
                key="entradas_data_fim_local",
                format="DD/MM/YYYY"
            )
        data_fim_query_entradas_local = datetime.combine(data_fim_entradas_local + timedelta(days=1), time.min)


        col_f_ent1, col_f_ent2 = st.columns(2)
        with col_f_ent1:
            codemp_input_str_ent = st.text_input(
                "Códigos de Empresa (CODEMP)",
                value="", # Sem valor padrão específico, usuário digita
                key="entradas_codemp_text",
                help="Digite um ou mais códigos separados por vírgula (ex: 21714, 21313)."
            )
            codigos_emp_selecionados_ent: Optional[List[int]] = None
            if codemp_input_str_ent.strip():
                try:
                    codigos_emp_selecionados_ent = [int(cod.strip()) for cod in codemp_input_str_ent.split(',') if cod.strip()]
                except ValueError:
                    st.warning("CODEMP inválido. Use números separados por vírgula.")
                    # Mantém como None ou lista vazia para não quebrar a query
                    codigos_emp_selecionados_ent = []
        
        with col_f_ent2:
            descricao_produto_ent = st.text_input(
                "Descrição do Produto (parte do nome)",
                value="", # Sem valor padrão, usuário digita
                key="entradas_descricao_text",
                help="Busca por parte da descrição. Ex: 'ATADURA GESS'"
            )
        
        
        coluna_marca , coluna_nota_fiscal = st.columns(2)
        # Filtro MARCA (usando a lista global da sidebar)
        # `marcas_list` deve estar disponível aqui (carregada na sidebar)
        with coluna_marca:
            marca_selecionada_ent = st.selectbox(
                "Marca do Produto",
                options=marcas_list, # Usa a lista de marcas carregada globalmente
                index=0, # Padrão "Todas"
                key="entradas_marca_select"
            )
        
        with coluna_nota_fiscal:
            nota_fiscal_filtro_ent = st.text_input(
            "Filtrar por NF",
            value="",
            key="entradas_nf_filter",
            help="Digite o número da NF (Nota Fiscal) para filtrar."
            )
        
        # Carrega os dados com base nos filtros
        # Trata o caso de codigos_emp_selecionados_ent ser uma lista vazia após um erro de input
        df_entradas = db.load_entradas_data(
            data_inicio=data_inicio_entradas_local,
            data_fim_query=data_fim_query_entradas_local,
            codigos_emp_list=codigos_emp_selecionados_ent if codigos_emp_selecionados_ent else None,
            descricao_produto=descricao_produto_ent.strip() if descricao_produto_ent.strip() else None,
            marca_produto=marca_selecionada_ent if marca_selecionada_ent != "Todas" else None,
            numero_nota_fiscal=nota_fiscal_filtro_ent.strip() if nota_fiscal_filtro_ent.strip() else None
        )

        if not df_entradas.empty:
            st.dataframe(
                df_entradas,
                use_container_width=True,
                hide_index=True,
                column_config={
                    C.COL_ENT_DATA: st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    C.COL_ENT_NOTA: st.column_config.TextColumn("NF"),
                    C.COL_ENT_CODEMP: st.column_config.TextColumn("Código BR"), # Ajustado para TextColumn se CODEMP for string
                    C.COL_ENT_DESCRICAO: st.column_config.TextColumn("Produto", width="large"),
                    C.COL_ENT_MARCA: st.column_config.TextColumn("Marca"),
                    C.COL_ENT_QUANTIDADE: st.column_config.NumberColumn("Quantidade", format="%.0f"), # ou "%.0f" se for sempre inteiro
                    C.COL_ENT_C_UNIT: st.column_config.NumberColumn("Custo Fornecedor", format="R$ %.2f"),
                    C.COL_ENT_CUSTO_M: st.column_config.NumberColumn("Custo SaudMed", format="R$ %.2f"),
                    C.COL_ENT_C_SUBTOTAL: st.column_config.NumberColumn("Subtotal", format="R$ %.2f"),
                },
                column_order=[ # Usando as constantes para a ordem
                    C.COL_ENT_DATA, C.COL_ENT_NOTA, C.COL_ENT_CODEMP, C.COL_ENT_DESCRICAO, C.COL_ENT_MARCA,
                    C.COL_ENT_QUANTIDADE, C.COL_ENT_C_UNIT, C.COL_ENT_CUSTO_M, C.COL_ENT_C_SUBTOTAL
                ]
            )
            utils.gerar_botao_download(df_entradas, "relatorio_entradas_produtos", key_suffix="_ent_tab")
        else:
            # Exibe mensagem apenas se algum filtro foi aplicado, para não poluir a tela inicialmente
            if any([codemp_input_str_ent.strip(), descricao_produto_ent.strip(), marca_selecionada_ent != "Todas"]):
                st.info("Nenhuma entrada de produto encontrada com os filtros selecionados.")
            else:
                st.info("Digite os filtros desejados para consultar as entradas de produtos.")


    # --- Sub-Aba: Vencimento
    with vencimento_tab:
        st.info('EM OBRAS')

    
    
    # --- Sub-Aba: Custo x Estoque
    with custoestoque_tab:
        st.caption("Produtos atualmente em estoque (saldo > 0, filial principal)")
        # Carrega dados de custo/estoque (aplicando filtros globais da sidebar)
        df_custo_estoque: pd.DataFrame = db.load_produtos_custo_estoque_data(
            marca_selecionada, produto_nome_filtro, categoria_selecionada
            )
        if not df_custo_estoque.empty:
            # Métricas
            try:
                metricas_prde: Dict[str, str] = {
                    "Produtos em Estoque": utils.formatar_inteiro(len(df_custo_estoque)), # Título mais claro
                    "Custo Total do Estoque": utils.formatar_moeda(df_custo_estoque[C.COL_CUSTO_TOTAL].sum())
                    }
                cols_prde = st.columns(len(metricas_prde))
                exibir_metricas(cols_prde, metricas_prde)
            except KeyError as e:
                st.error(f"Erro ao calcular métricas de Custo x Estoque: Coluna '{e}' não encontrada.")
            except Exception as e:
                st.error(f"Erro inesperado ao calcular métricas de Custo x Estoque: {e}")
            # Tabela
            st.dataframe(
                df_custo_estoque,
                use_container_width=True,
                hide_index=True,
                column_config={ # Títulos e formatos
                    C.COL_CODIGO: st.column_config.TextColumn("Código"),
                    C.COL_PRODUTO: st.column_config.TextColumn("Produto", width="large"),
                    C.COL_CUSTO_UNITARIO: st.column_config.NumberColumn("Custo Unitário", format="R$ %.2f", help="Custo registrado no banco de dados."),
                    C.COL_ESTOQUE: st.column_config.NumberColumn("Estoque", format="%.0f"), # Inteiro
                    C.COL_CUSTO_TOTAL: st.column_config.NumberColumn("Custo Total", format="R$ %.2f", help="Custo Unitário (DB) x Estoque Atual"),
                    },
                # Ordem das colunas (já vem ordenada por Custo Total da função load)
                column_order=(
                    C.COL_CODIGO, 
                    C.COL_PRODUTO, 
                    C.COL_CUSTO_UNITARIO, 
                    C.COL_ESTOQUE, 
                    C.COL_CUSTO_TOTAL
                    )
                )
            # Botão de Download
            utils.gerar_botao_download(
                df_custo_estoque,
                "custo_estoque_atual",
                key_suffix="_prde")
        else:
            # Mensagem se não houver dados
            st.info("Nenhum produto em estoque encontrado com os filtros selecionados.")



######################################################################################



#=======================================================================
# ABA 7: INFOSERVE
#=======================================================================

with tab_map["infoserve"]:
    st.header(C.TEXTO_IS_TITULO)
    st.caption(C.TEXTO_IS_DESCRICAO)
    
    # 1. Carregar os dados (usa a função original com cache)
    df_infoserve = utils.carregar_dados_infoserve_original_final()
    
    # 2. Verificar o resultado do carregamento
    if df_infoserve is None:
        # Erro crítico, mensagens já exibidas por utils
        st.warning("Falha ao carregar ou processar os dados da Infoserve.")
    elif df_infoserve.empty:
        # Arquivos lidos, mas sem dados válidos após processamento
        st.info(C.TEXTO_IS_SEM_DADOS)
    else:
        
        # --- 3. Seção de Filtros ---
        with st.expander(C.TEXTO_IS_FILTROS_EXPANDER, expanded=True): # Filtros visíveis por padrão
            col_filt1, col_filt2 = st.columns(2)
            
            with col_filt1:
                # Filtro de Data
                # Garante que a coluna de data existe e é do tipo datetime
                if C.COL_IS_DATA in df_infoserve.columns and pd.api.types.is_datetime64_any_dtype(df_infoserve[C.COL_IS_DATA]):
                    data_min_is = df_infoserve[C.COL_IS_DATA].min().date()
                    data_max_is = df_infoserve[C.COL_IS_DATA].max().date()
                else:
                    # Define padrões se a coluna de data estiver ausente ou com tipo incorreto
                    data_min_is = date.today()
                    data_max_is = date.today()
                    st.warning("Coluna de Data não encontrada ou inválida para filtro.")
                    
                data_inicio_is = st.date_input(
                    C.TEXTO_IS_FILTRO_DATA_INICIAL,
                    value=data_min_is,
                    min_value=data_min_is,
                    max_value=data_max_is,
                    key="infoserve_data_inicio", # Chave única para o widget
                    format="DD/MM/YYYY"
                )
                data_fim_is = st.date_input(
                    C.TEXTO_IS_FILTRO_DATA_FINAL,
                    value=data_max_is,
                    min_value=data_inicio_is, # Garante que fim não seja antes do início
                    max_value=data_max_is,
                    key="infoserve_data_fim", # Chave única para o widget
                    format="DD/MM/YYYY"
                )
                # Validação extra
                if data_fim_is < data_inicio_is:
                    st.warning(C.TEXTO_IS_FILTRO_AVISO_DATA)
                    # Não é necessário resetar, o widget st.date_input já impõe min_value
                    
            with col_filt2:
                # Filtro de Cliente
                if C.COL_IS_NOME_CLIENTE in df_infoserve.columns:
                    # Converte para string, trata NaNs, pega únicos e ordena
                    lista_clientes_is = sorted(df_infoserve[C.COL_IS_NOME_CLIENTE].astype(str).fillna("N/D").unique())
                else:
                    lista_clientes_is = ["N/D"]
                    st.warning("Coluna de Cliente não encontrada para filtro.")
                    
                clientes_selecionados_is = st.multiselect(
                    C.TEXTO_IS_FILTRO_CLIENTE,
                    options=lista_clientes_is,
                    default=[], # Nenhum selecionado por padrão
                    key="infoserve_cliente_multi" # Chave única
                )
                
                # Filtro de Produto
                if C.COL_IS_NOME_PRODUTO in df_infoserve.columns:
                    # Converte para string, trata NaNs, pega únicos e ordena
                    lista_produtos_is = sorted(df_infoserve[C.COL_IS_NOME_PRODUTO].astype(str).fillna("N/D").unique())
                else:
                    lista_produtos_is = ["N/D"]
                    st.warning("Coluna de Produto não encontrada para filtro.")
                    
                produtos_selecionados_is = st.multiselect(
                    C.TEXTO_IS_FILTRO_PRODUTO,
                    options=lista_produtos_is,
                    default=[], # Nenhum selecionado por padrão
                    key="infoserve_produto_multi" # Chave única
                )
                
        # --- 4. Aplicar Filtros ---
        df_infoserve_filtrado = df_infoserve.copy() # Começa com cópia dos dados completos
        
        # Aplica filtro de data (se a coluna for válida)
        if C.COL_IS_DATA in df_infoserve_filtrado.columns and pd.api.types.is_datetime64_any_dtype(df_infoserve_filtrado[C.COL_IS_DATA]):
            # Compara apenas a parte da data (.dt.date)
            df_infoserve_filtrado = df_infoserve_filtrado[
                (df_infoserve_filtrado[C.COL_IS_DATA].dt.date >= data_inicio_is) &
                (df_infoserve_filtrado[C.COL_IS_DATA].dt.date <= data_fim_is)
            ]
            
        # Aplica filtro de cliente (se houver seleção)
        if clientes_selecionados_is and C.COL_IS_NOME_CLIENTE in df_infoserve_filtrado.columns:
            df_infoserve_filtrado = df_infoserve_filtrado[
                df_infoserve_filtrado[C.COL_IS_NOME_CLIENTE].isin(clientes_selecionados_is)
            ]
            
        # Aplica filtro de produto (se houver seleção)
        if produtos_selecionados_is and C.COL_IS_NOME_PRODUTO in df_infoserve_filtrado.columns:
            df_infoserve_filtrado = df_infoserve_filtrado[
                df_infoserve_filtrado[C.COL_IS_NOME_PRODUTO].isin(produtos_selecionados_is)
            ]
            
        
        # --- 5. Exibição dos Dados Filtrados ---
        if df_infoserve_filtrado.empty:
            st.info(C.TEXTO_IS_FILTRO_SEM_RESULTADOS) # Mensagem se filtros não retornarem nada
        else:
            st.dataframe(
                df_infoserve_filtrado, # <--- EXIBE OS DADOS FILTRADOS
                hide_index=True,
                use_container_width=True,
                # Mantém a configuração de colunas
                column_config={
                    C.COL_IS_DATA: st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    C.COL_IS_NOTA: st.column_config.NumberColumn("Nota", format="%d"),
                    C.COL_IS_NOME_CLIENTE: st.column_config.TextColumn("Cliente"),
                    C.COL_IS_COD_PRODUTO: st.column_config.NumberColumn("Codigo", format="%d"), # Mantendo nome original da coluna final
                    C.COL_IS_NOME_PRODUTO: st.column_config.TextColumn("Producto"), # Mantendo nome original da coluna final
                    C.COL_IS_QTD: st.column_config.NumberColumn("Ctd", format="%d"), # Mantendo nome original da coluna final
                }
            )


            # --- 6. Botão de Download (para dados FILTRADOS) ---
            utils.gerar_botao_download(
            df_infoserve, # Passa o DataFrame
            "relatorio_infoserve", # Passa a base para o nome do arquivo
            key_suffix="_infoserve" # Passa o sufixo da chave
            )



######################################################################################



# --- Rodapé da Página ---
st.divider()
st.caption(f"© {datetime.now().year} SaudMed Analytics. Desenvolvido por Cássio Cândido Ribeiro.")



######################################################################################

# Printa no console
print('\nTÁ PRONTINHO')


######################################################################################



# Para rodar o código pelo CMD
# Copia e cola a linha abaixo no prompt:
# cd /d "C:\Users\Saudmed Terminal\Desktop\Cássio\saudmed_analytics\" && python -m streamlit run pagina_principal.py



######################################################################################