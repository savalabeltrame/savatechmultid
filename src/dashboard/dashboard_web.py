import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import date

# 1. CONFIGURACIÓN "ENTERPRISE" (Oculta menús de Streamlit)
st.set_page_config(
    page_title="Savatech Dados ERP | Inteligencia de Inventarios",
    page_icon="",
    layout="wide",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# CSS para ocultar el footer de Streamlit y dar estilo corporativo
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.header-container {
    background-color: #003366; /* Azul corporativo */
    color: white;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}
.metric-card {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #e9ecef;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# CARGA DE DATOS (Optimizada)
import os

# CARGA DE DATOS (Optimizada)
@st.cache_data
def cargar_datos():
    # Obtener la ruta base del proyecto (funciona en local y en Streamlit Cloud)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dados_dir = os.path.join(base_dir, 'dados')
    
    conn_sup = sqlite3.connect(os.path.join(dados_dir, 'inventario_supermercado.db'))
    df_sistema = pd.read_sql_query("SELECT * FROM stock_sistema", conn_sup)
    df_fisico = pd.read_sql_query("SELECT * FROM stock_fisico", conn_sup)
    conn_sup.close()
    
    df_comp = pd.merge(df_sistema, df_fisico[['codigo_producto', 'cantidad_fisica', 'observaciones']], on='codigo_producto', how='outer')
    df_comp['diferencia'] = df_comp['cantidad_fisica'] - df_comp['cantidad_sistema']
    
    def estado(row):
        if row['diferencia'] == 0: return 'Correcto'
        elif abs(row['diferencia']) >= 20: return 'Critico'
        else: return 'Diferencia'
    df_comp['estado'] = df_comp.apply(estado, axis=1)
    
    conn_fifo = sqlite3.connect(os.path.join(dados_dir, 'inventario_fifo.db'))
    df_prod = pd.read_sql_query("SELECT * FROM productos", conn_fifo)
    df_lotes = pd.read_sql_query("SELECT * FROM lotes_inventario", conn_fifo)
    conn_fifo.close()
    
    df_fifo = pd.merge(df_lotes, df_prod, on='codigo_producto', how='left')
    df_fifo['fecha_vencimiento'] = pd.to_datetime(df_fifo['fecha_vencimiento'])
    df_fifo['dias_para_vencer'] = (df_fifo['fecha_vencimiento'] - pd.Timestamp(date.today())).dt.days
    df_fifo['valor_lote'] = df_fifo['cantidad_actual'] * df_fifo['costo_unitario']
    
    return df_comp, df_fifo
df_comp, df_fifo = cargar_datos()

# 2. HEADER CORPORATIVO
st.markdown("""
<div class="header-container">
    <h1 style="margin:0;">Savatech Dados ERP</h1>
    <h3 style="margin:5px 0 0 0; font-weight:normal;">Módulo de Inteligencia y Auditoría de Inventarios</h3>
</div>
""", unsafe_allow_html=True)

# 3. BARRA LATERAL (Simulación de Software Real)
st.sidebar.markdown("### ⚙️ Configuración del Módulo")
st.sidebar.success("✅ Sistema Conectado al ERP")
st.sidebar.info(f"👤 Usuario: Gerente de Operaciones")

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtros de Auditoría")

categorias = ['Todas'] + list(df_comp['categoria'].unique())
cat_sel = st.sidebar.selectbox("Categoría de Producto", categorias)

estados = ['Todos'] + list(df_comp['estado'].unique())
estado_sel = st.sidebar.selectbox("Estado de Conciliación", estados)

dias_filtro = st.sidebar.slider("Radar de Vencimiento (Próximos X días)", 0, 90, 30)

# Lógica de filtros
df_filtrado = df_comp.copy()
if cat_sel != 'Todas': df_filtrado = df_filtrado[df_filtrado['categoria'] == cat_sel]
if estado_sel != 'Todos': df_filtrado = df_filtrado[df_filtrado['estado'] == estado_sel]

# 4. PESTAÑAS EJECUTIVAS (Tabs)
tab_resumen, tab_auditoria, tab_fifo = st.tabs([
    "📊 Resumen Ejecutivo", 
    "🔍 Auditoría de Stock (Sistema vs Físico)", 
    "📅 Radar de Vencimientos (FIFO)"
])

# --- PESTAÑA 1: RESUMEN EJECUTIVO ---
with tab_resumen:
    st.subheader("Indicadores Clave de Desempeño (KPIs)")
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(df_filtrado)
    correctos = len(df_filtrado[df_filtrado['estado'] == 'Correcto'])
    criticos = len(df_filtrado[df_filtrado['estado'] == 'Critico'])
    tasa = (correctos/total*100) if total > 0 else 0
    valor_inv = df_fifo['valor_lote'].sum()
    
    with col1:
        st.metric("Precisión de Inventario", f"{tasa:.1f}%", delta=f"{tasa - 80:.1f}% vs Meta")
    with col2:
        st.metric("Alertas Críticas", criticos, delta="Requiere acción")
    with col3:
        st.metric("Valor Total en Inventario", f"R$ {valor_inv:,.2f}")
    with col4:
        st.metric("Lotes en Riesgo", len(df_fifo[df_fifo['dias_para_vencer'] <= dias_filtro]))

    st.markdown("---")

    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Salud del Inventario")
        fig_pie = px.pie(df_filtrado, names='estado', color='estado', 
                         color_discrete_map={'Correcto': '#28a745', 'Diferencia': '#ffc107', 'Critico': '#dc3545'},
                         hole=0.5)
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_g2:
        st.subheader("Impacto Financiero por Categoría")
        df_valor_cat = df_fifo.groupby('categoria')['valor_lote'].sum().reset_index()
        fig_cat = px.bar(df_valor_cat, x='categoria', y='valor_lote', color='categoria',
                         labels={'categoria': 'Categoría', 'valor_lote': 'Valor (R$)'})
        fig_cat.update_layout(showlegend=False)
        st.plotly_chart(fig_cat, use_container_width=True)

# --- PESTAÑA 2: AUDITORÍA DE STOCK ---
with tab_auditoria:
    st.subheader("Conciliación: Inventario en Sistema vs Inventario Físico")
    st.info("Este módulo detecta automáticamente fugas, robos o errores de recepción.")
    
    df_diff = df_filtrado[df_filtrado['diferencia'] != 0]
    if not df_diff.empty:
        fig_bar = px.bar(df_diff, x='nombre_producto', y='diferencia', color='estado',
                        color_discrete_map={'Diferencia': '#ffc107', 'Critico': '#dc3545'},
                        labels={'diferencia': 'Unidades de Diferencia'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.success("¡Excelente! No hay diferencias en los filtros seleccionados.")
        
    st.subheader("Detalle de Productos")
    st.dataframe(df_filtrado[['codigo_producto', 'nombre_producto', 'categoria', 'cantidad_sistema', 'cantidad_fisica', 'diferencia', 'estado']], use_container_width=True)

# --- PESTAÑA 3: RADAR FIFO ---
with tab_fifo:
    st.subheader(f"Radar de Vencimiento: Lotes que vencen en los próximos {dias_filtro} días")
    
    df_venc = df_fifo[(df_fifo['dias_para_vencer'] <= dias_filtro) & (df_fifo['dias_para_vencer'] >= 0)].copy()
    
    if not df_venc.empty:
        fig_venc = px.bar(df_venc, x='nombre_producto', y='dias_para_vencer', color='dias_para_vencer',
                         color_continuous_scale=['#28a745', '#ffc107', '#fd7e14', '#dc3545'],
                         labels={'dias_para_vencer': 'Días restantes'},
                         hover_data=['numero_lote', 'cantidad_actual', 'fecha_vencimiento', 'valor_lote'])
        st.plotly_chart(fig_venc, use_container_width=True)
        
        st.subheader("Lotes Prioritarios para Promoción o Baja")
        st.dataframe(df_venc[['codigo_producto', 'nombre_producto', 'numero_lote', 'fecha_vencimiento', 'dias_para_vencer', 'cantidad_actual', 'valor_lote']], use_container_width=True)
    else:
        st.success(f"✅ No hay lotes próximos a vencer en los próximos {dias_filtro} días.")

# FOOTER CORPORATIVO
st.markdown("---")
st.caption(f"Savatech Dados ERP | Módulo de Inteligencia de Inventarios v1.0 | Última actualización: {date.today().strftime('%d/%m/%Y %H:%M')}")