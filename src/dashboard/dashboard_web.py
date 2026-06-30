import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import os
import io
import numpy as np
from scipy import stats

# 1. CONFIGURACIÓN "ENTERPRISE"
st.set_page_config(
    page_title="Savatech Dados ERP | Inteligencia de Inventarios",
    page_icon="📊",
    layout="wide",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# CSS Corporativo
hide_streamlit_style = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&display=swap');
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.header-container {
    background: linear-gradient(135deg, #065f46 0%, #047857 100%);
    color: white;
    padding: 25px;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.header-container h1 { font-family: 'Playfair Display', serif; font-weight: 900; font-size: 2.5rem; margin: 0; }
.header-container h3 { font-family: 'Segoe UI', sans-serif; font-weight: 300; margin: 8px 0 0 0; opacity: 0.95; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ============================================
# FUNCIONES DE ANÁLISIS AVANZADO
# ============================================
def predecir_vencimientos(df_fifo, dias_futuros=30):
    df_venc = df_fifo[df_fifo['dias_para_vencer'] >= 0].copy()
    venc_por_dia = df_venc.groupby('dias_para_vencer').size().reset_index(name='cantidad')
    venc_por_dia['media_movil_7d'] = venc_por_dia['cantidad'].rolling(window=7, min_periods=1).mean()
    return venc_por_dia

def calcular_top_problematicos(df_comp, top_n=10):
    df_problemas = df_comp[df_comp['diferencia'] != 0].copy()
    if 'precio_venta' in df_problemas.columns:
        df_problemas['valor_diferencia'] = abs(df_problemas['diferencia']) * df_problemas['precio_venta']
    else:
        df_problemas['valor_diferencia'] = abs(df_problemas['diferencia'])
    
    top_productos = df_problemas.groupby('nombre_producto').agg({
        'diferencia': 'sum', 'valor_diferencia': 'sum', 'codigo_producto': 'count'
    }).round(2).reset_index()
    top_productos.columns = ['Producto', 'Diferencia Total', 'Valor Perdido', 'Frecuencia']
    return top_productos.sort_values('Valor Perdido', ascending=False).head(top_n)

def calcular_kpis_avanzados(df_comp, df_fifo):
    kpis = {}
    total_productos = len(df_comp)
    productos_con_movimiento = len(df_comp[df_comp['diferencia'] != 0])
    kpis['giro_inventario'] = (productos_con_movimiento / total_productos * 100) if total_productos > 0 else 0
    
    productos_vencidos = len(df_fifo[df_fifo['dias_para_vencer'] < 0])
    total_lotes = len(df_fifo)
    kpis['tasa_obsolescencia'] = (productos_vencidos / total_lotes * 100) if total_lotes > 0 else 0
    
    kpis['valor_promedio_producto'] = df_fifo['valor_lote'].mean() if 'valor_lote' in df_fifo.columns else 0
    return kpis

# ============================================
# CARGA DE DATOS (Incluye ERP Simulado Seguro)
# ============================================
@st.cache_data
def cargar_datos():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dados_dir = os.path.join(base_dir, 'dados')
    
    # 1. Base de datos de Supermercado (Auditoría)
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
    
    # 2. Base de datos FIFO (Vencimientos)
    conn_fifo = sqlite3.connect(os.path.join(dados_dir, 'inventario_fifo.db'))
    df_prod = pd.read_sql_query("SELECT * FROM productos", conn_fifo)
    df_lotes = pd.read_sql_query("SELECT * FROM lotes_inventario", conn_fifo)
    conn_fifo.close()
    
    df_fifo = pd.merge(df_lotes, df_prod, on='codigo_producto', how='left')
    df_fifo['fecha_vencimiento'] = pd.to_datetime(df_fifo['fecha_vencimiento'])
    df_fifo['dias_para_vencer'] = (df_fifo['fecha_vencimiento'] - pd.Timestamp(date.today())).dt.days
    df_fifo['valor_lote'] = df_fifo['cantidad_actual'] * df_fifo['costo_unitario']

    # 3. 🔗 CONEXIÓN SEGURA AL ERP SIMULADO (MODO SOLO LECTURA)
    db_erp_path = os.path.join(dados_dir, 'erp_simulado_totvs.db')
    uri_erp = f"file:{db_erp_path}?mode=ro" # 🔒 BLOQUEO DE ESCRITURA
    conn_erp = sqlite3.connect(uri_erp, uri=True)
    
    df_erp_prod = pd.read_sql_query("SELECT * FROM ERP_PRODUCTOS", conn_erp)
    df_erp_stock = pd.read_sql_query("SELECT * FROM ERP_STOCK", conn_erp)
    df_erp_mov = pd.read_sql_query("SELECT * FROM ERP_MOVIMIENTOS", conn_erp)
    conn_erp.close()
    
    return df_comp, df_fifo, df_erp_prod, df_erp_stock, df_erp_mov

df_comp, df_fifo, df_erp_prod, df_erp_stock, df_erp_mov = cargar_datos()

# 2. HEADER CORPORATIVO
st.markdown("""
<div class="header-container">
    <h1>Savatech Dados ERP</h1>
    <h3>Módulo de Inteligencia y Auditoría de Inventarios</h3>
</div>
""", unsafe_allow_html=True)

# 3. BARRA LATERAL
st.sidebar.markdown("### ⚙️ Configuración del Módulo")
st.sidebar.success("✅ Sistema Conectado al ERP")
st.sidebar.info(f"👤 Usuario: Gerente de Operaciones")
st.sidebar.markdown("---")
st.sidebar.header(" Filtros de Auditoría")

categorias = ['Todas'] + list(df_comp['categoria'].unique())
cat_sel = st.sidebar.selectbox("Categoría de Producto", categorias)
estados = ['Todos'] + list(df_comp['estado'].unique())
estado_sel = st.sidebar.selectbox("Estado de Conciliación", estados)
dias_filtro = st.sidebar.slider("Radar de Vencimiento (Próximos X días)", 0, 90, 30)

df_filtrado = df_comp.copy()
if cat_sel != 'Todas': df_filtrado = df_filtrado[df_filtrado['categoria'] == cat_sel]
if estado_sel != 'Todos': df_filtrado = df_filtrado[df_filtrado['estado'] == estado_sel]

# 4. PESTAÑAS EJECUTIVAS (5 Pestañas)
tab_resumen, tab_auditoria, tab_fifo, tab_analise, tab_erp = st.tabs([
    " Resumen Ejecutivo", 
    "🔍 Auditoría de Stock", 
    "📅 Radar FIFO",
    "📈 Análisis Avanzado",
    "🔗 Conexión ERP en Vivo"
])

# --- PESTAÑA 1: RESUMEN EJECUTIVO ---
with tab_resumen:
    st.subheader("Indicadores Clave de Desempeño (KPIs)")
    col1, col2, col3, col4 = st.columns(4)
    total = len(df_filtrado)
    correctos = len(df_filtrado[df_filtrado['estado'] == 'Correcto'])
    criticos = len(df_filtrado[df_filtrado['estado'] == 'Critico'])
    tasa = (correctos/total*100) if total > 0 else 0
    valor_inv = df_fifo['valor_lote'].sum() if 'valor_lote' in df_fifo.columns else 0
    
    with col1: st.metric("Precisión de Inventario", f"{tasa:.1f}%", delta=f"{tasa - 80:.1f}% vs Meta")
    with col2: st.metric("Alertas Críticas", criticos, delta="Requiere acción")
    with col3: st.metric("Valor Total en Inventario", f"R$ {valor_inv:,.2f}")
    with col4: st.metric("Lotes en Riesgo", len(df_fifo[df_fifo['dias_para_vencer'] <= dias_filtro]))

    st.markdown("---")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Salud del Inventario")
        fig_pie = px.pie(df_filtrado, names='estado', color='estado', 
                         color_discrete_map={'Correcto': '#10b981', 'Diferencia': '#f59e0b', 'Critico': '#dc2626'}, hole=0.5)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_g2:
        st.subheader("Impacto Financiero por Categoría")
        df_valor_cat = df_fifo.groupby('categoria')['valor_lote'].sum().reset_index() if 'valor_lote' in df_fifo.columns else pd.DataFrame()
        if not df_valor_cat.empty:
            fig_cat = px.bar(df_valor_cat, x='categoria', y='valor_lote', color='categoria',
                             color_discrete_sequence=['#065f46', '#10b981', '#34d399', '#6ee7b7', '#a7f3d0'])
            st.plotly_chart(fig_cat, use_container_width=True)
    
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        st.download_button(label="📥 Descargar Resumen (CSV)", data=df_filtrado.to_csv(index=False).encode('utf-8'), file_name='resumen.csv', mime='text/csv', use_container_width=True)
    with col_btn2:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: df_filtrado.to_excel(writer, index=False, sheet_name='Resumen')
        output.seek(0)
        st.download_button(label="📥 Descargar Resumen (Excel)", data=output, file_name='resumen.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)

# --- PESTAÑA 2: AUDITORÍA DE STOCK ---
with tab_auditoria:
    st.subheader("Conciliación: Inventario en Sistema vs Inventario Físico")
    df_diff = df_filtrado[df_filtrado['diferencia'] != 0]
    if not df_diff.empty:
        fig_bar = px.bar(df_diff, x='nombre_producto', y='diferencia', color='estado', color_discrete_map={'Diferencia': '#f59e0b', 'Critico': '#dc2626'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else: st.success("¡Excelente! No hay diferencias en los filtros seleccionados.")
    st.dataframe(df_filtrado[['codigo_producto', 'nombre_producto', 'categoria', 'cantidad_sistema', 'cantidad_fisica', 'diferencia', 'estado']], use_container_width=True)

# --- PESTAÑA 3: RADAR FIFO ---
with tab_fifo:
    st.subheader(f"Radar de Vencimiento: Lotes que vencen en los próximos {dias_filtro} días")
    df_venc = df_fifo[(df_fifo['dias_para_vencer'] <= dias_filtro) & (df_fifo['dias_para_vencer'] >= 0)].copy()
    if not df_venc.empty:
        fig_venc = px.bar(df_venc, x='nombre_producto', y='dias_para_vencer', color='dias_para_vencer', color_continuous_scale=['#065f46', '#10b981', '#f59e0b', '#dc2626'])
        st.plotly_chart(fig_venc, use_container_width=True)
        st.dataframe(df_venc[['codigo_producto', 'nombre_producto', 'numero_lote', 'fecha_vencimiento', 'dias_para_vencer', 'cantidad_actual']], use_container_width=True)
    else: st.success(f"✅ No hay lotes próximos a vencer en los próximos {dias_filtro} días.")
    
    st.markdown("---")
    st.subheader("📊 Indicadores Avanzados de Gestión")
    kpis = calcular_kpis_avanzados(df_comp, df_fifo)
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1: st.metric("Giro de Inventario", f"{kpis['giro_inventario']:.1f}%")
    with col_kpi2: st.metric("Tasa de Obsolescencia", f"{kpis['tasa_obsolescencia']:.1f}%", delta="⚠️" if kpis['tasa_obsolescencia'] > 5 else "✅")
    with col_kpi3: st.metric("Valor Promedio por Lote", f"R$ {kpis['valor_promedio_producto']:,.2f}")

# --- PESTAÑA 4: ANÁLISIS AVANZADO ---
with tab_analise:
    st.subheader("🎯 Análisis de Rentabilidad por Categoría")
    if 'valor_lote' in df_fifo.columns:
        df_cat = df_fifo.groupby('categoria').agg({'valor_lote': ['sum', 'mean', 'count'], 'dias_para_vencer': 'mean'}).round(2).reset_index()
        df_cat.columns = ['Categoria', 'Valor Total', 'Valor Promedio', 'Cantidad', 'Días Promedio Vencimiento']
        df_cat = df_cat.sort_values('Valor Total', ascending=False)
        col_cat1, col_cat2 = st.columns(2)
        with col_cat1:
            fig_cat_bar = px.bar(df_cat, x='Categoria', y='Valor Total', color='Valor Total', color_continuous_scale='Viridis')
            st.plotly_chart(fig_cat_bar, use_container_width=True)
        with col_cat2: st.dataframe(df_cat.style.format({'Valor Total': 'R$ {:,.2f}', 'Valor Promedio': 'R$ {:,.2f}'}), use_container_width=True)

# ============================================
# 🔗 PESTAÑA 5: CONEXIÓN ERP EN VIVO (NUEVA)
# ============================================
with tab_erp:
    st.subheader("🔗 Integración Segura con ERP (Modo Solo Lectura)")
    
    # Indicador de seguridad
    st.success("🛡️ **Conexión Activa y Segura:** `file:erp_simulado_totvs.db?mode=ro`")
    st.info("Este módulo demuestra cómo Savatech se conecta a su ERP (TOTVS, SAP, Sankhya) **sin riesgo** de modificar, borrar o alterar sus datos operativos. La base de datos está físicamente bloqueada para escritura.")
    
    st.markdown("---")
    
    # 1. Catálogo de Productos
    st.subheader("📦 1. Catálogo de Productos (Tabla SB1 simulada)")
    st.caption("Datos leídos directamente del ERP del cliente.")
    st.dataframe(df_erp_prod, use_container_width=True)
    
    st.markdown("---")
    
    # 2. Saldos de Stock
    st.subheader("🏭 2. Saldos de Stock por Almacén (Tabla SB2 simulada)")
    st.caption("Inventario actualizado en tiempo real.")
    st.dataframe(df_erp_stock, use_container_width=True)
    
    st.markdown("---")
    
    # 3. Movimientos
    st.subheader("🚚 3. Últimos Movimientos / Notas Fiscales (Tabla SD1 simulada)")
    st.caption("Historial de entradas y salidas.")
    st.dataframe(df_erp_mov, use_container_width=True)

# FOOTER CORPORATIVO
st.markdown("---")
st.caption(f"Savatech Dados ERP | Módulo de Inteligencia de Inventarios v1.0 | Última actualización: {date.today().strftime('%d/%m/%Y %H:%M')}")