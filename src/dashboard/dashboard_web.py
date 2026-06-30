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

# CSS para ocultar el footer de Streamlit y dar estilo corporativo VERDE con fuente Playfair
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
.header-container h1 {
    font-family: 'Playfair Display', serif;
    font-weight: 900;
    font-size: 2.5rem;
    margin: 0;
    letter-spacing: 1px;
}
.header-container h3 {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-weight: 300;
    margin: 8px 0 0 0;
    opacity: 0.95;
}
.metric-card {
    background-color: #f0fdf4;
    padding: 15px;
    border-radius: 12px;
    border: 2px solid #10b981;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ============================================
# FUNCIONES DE ANÁLISIS AVANZADO
# ============================================

def predecir_vencimientos(df_fifo, dias_futuros=30):
    """Predice vencimientos futuros basados en tendencia histórica"""
    df_venc = df_fifo[df_fifo['dias_para_vencer'] >= 0].copy()
    
    # Agrupar por días
    venc_por_dia = df_venc.groupby('dias_para_vencer').size().reset_index(name='cantidad')
    
    # Calcular media móvil
    venc_por_dia['media_movil_7d'] = venc_por_dia['cantidad'].rolling(window=7, min_periods=1).mean()
    
    return venc_por_dia

def calcular_top_problematicos(df_comp, top_n=10):
    """Calcula los top N productos con más problemas"""
    df_problemas = df_comp[df_comp['diferencia'] != 0].copy()
    
    # Si existe la columna precio_venta, usarla. Si no, usar 1
    if 'precio_venta' in df_problemas.columns:
        df_problemas['valor_diferencia'] = abs(df_problemas['diferencia']) * df_problemas['precio_venta']
    else:
        df_problemas['valor_diferencia'] = abs(df_problemas['diferencia'])
    
    top_productos = df_problemas.groupby('nombre_producto').agg({
        'diferencia': 'sum',
        'valor_diferencia': 'sum',
        'codigo_producto': 'count'
    }).round(2).reset_index()
    
    top_productos.columns = ['Producto', 'Diferencia Total', 'Valor Perdido', 'Frecuencia']
    top_productos = top_productos.sort_values('Valor Perdido', ascending=False).head(top_n)
    
    return top_productos

def calcular_kpis_avanzados(df_comp, df_fifo):
    """Calcula KPIs avanzados de inventario"""
    kpis = {}
    
    # Giro de inventario (simplificado)
    total_productos = len(df_comp)
    productos_con_movimiento = len(df_comp[df_comp['diferencia'] != 0])
    kpis['giro_inventario'] = (productos_con_movimiento / total_productos * 100) if total_productos > 0 else 0
    
    # Tasa de obsolescencia
    productos_vencidos = len(df_fifo[df_fifo['dias_para_vencer'] < 0])
    total_lotes = len(df_fifo)
    kpis['tasa_obsolescencia'] = (productos_vencidos / total_lotes * 100) if total_lotes > 0 else 0
    
    # Valor promedio por producto
    if 'valor_lote' in df_fifo.columns:
        kpis['valor_promedio_producto'] = df_fifo['valor_lote'].mean()
    else:
        kpis['valor_promedio_producto'] = 0
    
    return kpis

# ============================================
# FIN DE FUNCIONES DE ANÁLISIS AVANZADO
# ============================================

# CARGA DE DATOS (Optimizada)
@st.cache_data
def cargar_datos():
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

# 2. HEADER CORPORATIVO VERDE con Playfair Display
st.markdown("""
<div class="header-container">
    <h1>Savatech Dados ERP</h1>
    <h3>Módulo de Inteligencia y Auditoría de Inventarios</h3>
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
tab_resumen, tab_auditoria, tab_fifo, tab_analise = st.tabs([
    "📊 Resumen Ejecutivo", 
    "🔍 Auditoría de Stock (Sistema vs Físico)", 
    "📅 Radar de Vencimientos (FIFO)",
    "📈 Análisis Avanzado"
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
                         color_discrete_map={'Correcto': '#10b981', 'Diferencia': '#f59e0b', 'Critico': '#dc2626'},
                         hole=0.5)
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_g2:
        st.subheader("Impacto Financiero por Categoría")
        df_valor_cat = df_fifo.groupby('categoria')['valor_lote'].sum().reset_index() if 'valor_lote' in df_fifo.columns else pd.DataFrame()
        if not df_valor_cat.empty:
            fig_cat = px.bar(df_valor_cat, x='categoria', y='valor_lote', color='categoria',
                             color_discrete_sequence=['#065f46', '#10b981', '#34d399', '#6ee7b7', '#a7f3d0'],
                             labels={'categoria': 'Categoría', 'valor_lote': 'Valor (R$)'})
            fig_cat.update_layout(showlegend=False)
            st.plotly_chart(fig_cat, use_container_width=True)
    
    # Botones de descarga para resumen
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        st.download_button(
            label="📥 Descargar Resumen (CSV)",
            data=df_filtrado.to_csv(index=False).encode('utf-8'),
            file_name='resumen_inventario.csv',
            mime='text/csv',
            use_container_width=True
        )
    with col_btn2:
        # Crear Excel en memoria usando BytesIO
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='Resumen')
        output.seek(0)
        
        st.download_button(
            label="📥 Descargar Resumen (Excel)",
            data=output,
            file_name='resumen_inventario.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True
        )
    
    # NUEVA SECCIÓN: Análisis Predictivo
    st.markdown("---")
    st.subheader("📈 Análisis Predictivo")
    
    col_pred1, col_pred2 = st.columns(2)
    
    with col_pred1:
        st.markdown("#### Tendencia de Vencimientos")
        df_prediccion = predecir_vencimientos(df_fifo, dias_filtro)
        
        if not df_prediccion.empty:
            fig_tendencia = px.line(
                df_prediccion.head(30),
                x='dias_para_vencer',
                y='media_movil_7d',
                title='Vencimientos Próximos (Media Móvil 7 días)',
                labels={'dias_para_vencer': 'Días', 'media_movil_7d': 'Cantidad de Productos'}
            )
            fig_tendencia.update_traces(line=dict(color='#2563eb', width=3))
            st.plotly_chart(fig_tendencia, use_container_width=True)
    
    with col_pred2:
        st.markdown("#### Distribución por Tiempo")
        df_temp = df_fifo[df_fifo['dias_para_vencer'] >= 0].copy()
        if not df_temp.empty:
            df_temp['periodo'] = pd.cut(
                df_temp['dias_para_vencer'],
                bins=[0, 7, 15, 30, 60, 90, float('inf')],
                labels=['0-7 días', '8-15 días', '16-30 días', '31-60 días', '61-90 días', '+90 días']
            )
            
            fig_periodo = px.pie(
                df_temp,
                names='periodo',
                title='Distribución por Período de Vencimiento',
                hole=0.4
            )
            st.plotly_chart(fig_periodo, use_container_width=True)

# --- PESTAÑA 2: AUDITORÍA DE STOCK ---
with tab_auditoria:
    st.subheader("Conciliación: Inventario en Sistema vs Inventario Físico")
    st.info("Este módulo detecta automáticamente fugas, robos o errores de recepción.")
    
    df_diff = df_filtrado[df_filtrado['diferencia'] != 0]
    if not df_diff.empty:
        fig_bar = px.bar(df_diff, x='nombre_producto', y='diferencia', color='estado',
                        color_discrete_map={'Diferencia': '#f59e0b', 'Critico': '#dc2626'},
                        labels={'diferencia': 'Unidades de Diferencia'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.success("¡Excelente! No hay diferencias en los filtros seleccionados.")
        
    st.subheader("Detalle de Productos")
    st.dataframe(df_filtrado[['codigo_producto', 'nombre_producto', 'categoria', 'cantidad_sistema', 'cantidad_fisica', 'diferencia', 'estado']], use_container_width=True)
    
    # Botón de descarga para auditoría
    st.markdown("---")
    st.download_button(
        label="📥 Descargar Auditoría Completa (CSV)",
        data=df_filtrado.to_csv(index=False).encode('utf-8'),
        file_name='auditoria_stock.csv',
        mime='text/csv',
        use_container_width=True
    )
    
    # NUEVA SECCIÓN: Top Productos Problemáticos
    st.markdown("---")
    st.subheader("🔴 Top 10 Productos con Mayores Pérdidas")
    
    df_top = calcular_top_problematicos(df_filtrado, top_n=10)
    
    if not df_top.empty:
        col_top1, col_top2 = st.columns(2)
        
        with col_top1:
            fig_top_bar = px.bar(
                df_top,
                x='Valor Perdido',
                y='Producto',
                orientation='h',
                title='Valor Perdido por Producto',
                color='Valor Perdido',
                color_continuous_scale='Reds'
            )
            fig_top_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_top_bar, use_container_width=True)
        
    with col_top2:
            # Formatear el dataframe sin usar style
            df_top_formateado = df_top.copy()
            df_top_formateado['Valor Perdido'] = df_top_formateado['Valor Perdido'].apply(lambda x: f'R$ {x:,.2f}')
            
 
# --- PESTAÑA 3: RADAR FIFO ---
with tab_fifo:
    st.subheader(f"Radar de Vencimiento: Lotes que vencen en los próximos {dias_filtro} días")
    
    df_venc = df_fifo[(df_fifo['dias_para_vencer'] <= dias_filtro) & (df_fifo['dias_para_vencer'] >= 0)].copy()
    
    if not df_venc.empty:
        fig_venc = px.bar(df_venc, x='nombre_producto', y='dias_para_vencer', color='dias_para_vencer',
                         color_continuous_scale=['#065f46', '#10b981', '#f59e0b', '#dc2626'],
                         labels={'dias_para_vencer': 'Días restantes'},
                         hover_data=['numero_lote', 'cantidad_actual', 'fecha_vencimiento', 'valor_lote'])
        st.plotly_chart(fig_venc, use_container_width=True)
        
        st.subheader("Lotes Prioritarios para Promoción o Baja")
        st.dataframe(df_venc[['codigo_producto', 'nombre_producto', 'numero_lote', 'fecha_vencimiento', 'dias_para_vencer', 'cantidad_actual', 'valor_lote']], use_container_width=True)
        
        # Botón de descarga para FIFO
        st.markdown("---")
        st.download_button(
            label="📥 Descargar Lotes en Riesgo (CSV)",
            data=df_venc.to_csv(index=False).encode('utf-8'),
            file_name='lotes_vencimiento.csv',
            mime='text/csv',
            use_container_width=True
        )
    else:
        st.success(f"✅ No hay lotes próximos a vencer en los próximos {dias_filtro} días.")
    
    # NUEVA SECCIÓN: KPIs Avanzados
    st.markdown("---")
    st.subheader("📊 Indicadores Avanzados de Gestión")
    
    kpis = calcular_kpis_avanzados(df_comp, df_fifo)
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    
    with col_kpi1:
        st.metric(
            label="Giro de Inventario",
            value=f"{kpis['giro_inventario']:.1f}%",
            help="Porcentaje de productos con movimiento"
        )
    
    with col_kpi2:
        st.metric(
            label="Tasa de Obsolescencia",
            value=f"{kpis['tasa_obsolescencia']:.1f}%",
            delta=f"{'⚠️' if kpis['tasa_obsolescencia'] > 5 else '✅'}",
            help="Porcentaje de productos vencidos"
        )
    
    with col_kpi3:
        st.metric(
            label="Valor Promedio por Lote",
            value=f"R$ {kpis['valor_promedio_producto']:,.2f}",
            help="Valor promedio de cada lote en inventario"
        )

# --- PESTAÑA 4: ANÁLISIS AVANZADO ---
with tab_analise:
    st.subheader("🎯 Análisis de Rentabilidad por Categoría")
    
    # Agrupar por categoría
    if 'valor_lote' in df_fifo.columns:
        df_cat = df_fifo.groupby('categoria').agg({
            'valor_lote': ['sum', 'mean', 'count'],
            'dias_para_vencer': 'mean'
        }).round(2).reset_index()
        
        df_cat.columns = ['Categoria', 'Valor Total', 'Valor Promedio', 'Cantidad', 'Días Promedio Vencimiento']
        df_cat = df_cat.sort_values('Valor Total', ascending=False)
        
        col_cat1, col_cat2 = st.columns(2)
        
        with col_cat1:
            fig_cat_bar = px.bar(
                df_cat,
                x='Categoria',
                y='Valor Total',
                title='Valor Total en Inventario por Categoría',
                color='Valor Total',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_cat_bar, use_container_width=True)
        
        with col_cat2:
            st.dataframe(
                df_cat.style.format({
                    'Valor Total': 'R$ {:,.2f}',
                    'Valor Promedio': 'R$ {:,.2f}',
                    'Días Promedio Vencimiento': '{:.1f} días'
                }),
                use_container_width=True
            )
    else:
        st.warning("No hay datos de valor de lote disponibles para el análisis.")
    
    # Heatmap de pérdidas por categoría
    st.markdown("---")
    st.subheader("🔥 Mapa de Calor: Pérdidas por Categoría")
    
    df_heat = df_comp[df_comp['diferencia'] != 0].groupby(['categoria', 'estado']).size().reset_index(name='cantidad')
    
    if not df_heat.empty:
        fig_heat = px.density_heatmap(
            df_heat,
            x='categoria',
            y='estado',
            z='cantidad',
            title='Distribución de Diferencias por Categoría y Estado',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.success("¡Excelente! No hay diferencias significativas por categoría.")

# FOOTER CORPORATIVO
st.markdown("---")
st.caption(f"Savatech Dados ERP | Módulo de Inteligencia de Inventarios v1.0 | Última actualización: {date.today().strftime('%d/%m/%Y %H:%M')}")