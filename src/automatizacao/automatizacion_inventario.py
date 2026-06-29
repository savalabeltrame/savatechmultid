import sqlite3
import pandas as pd
from datetime import datetime, date
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header

print("=" * 70)
print("AUDITORIA AUTOMATICA DE INVENTARIO")
print("=" * 70)

DATA_HOJE = datetime.now().strftime('%Y%m%d')
PASTA_RELATORIOS = 'relatorios_automaticos'
os.makedirs(PASTA_RELATORIOS, exist_ok=True)

try:
    print("\nAnalizando inventario_supermercado.db...")
    conn_sup = sqlite3.connect('inventario_supermercado.db')
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
    
    print("Analizando inventario_fifo.db...")
    conn_fifo = sqlite3.connect('inventario_fifo.db')
    df_prod = pd.read_sql_query("SELECT * FROM productos", conn_fifo)
    df_lotes = pd.read_sql_query("SELECT * FROM lotes_inventario", conn_fifo)
    conn_fifo.close()
    
    df_fifo = pd.merge(df_lotes, df_prod, on='codigo_producto', how='left')
    df_fifo['fecha_vencimiento'] = pd.to_datetime(df_fifo['fecha_vencimiento'])
    df_fifo['dias_para_vencer'] = (df_fifo['fecha_vencimiento'] - pd.Timestamp(date.today())).dt.days
    df_fifo['valor_lote'] = df_fifo['cantidad_actual'] * df_fifo['costo_unitario']
    
    print("Calculando KPIs...")
    total_produtos = len(df_comp)
    produtos_corretos = len(df_comp[df_comp['estado'] == 'Correcto'])
    produtos_criticos = len(df_comp[df_comp['estado'] == 'Critico'])
    lotes_vencidos = len(df_fifo[df_fifo['dias_para_vencer'] < 0])
    valor_risco = df_fifo[df_fifo['dias_para_vencer'] <= 7]['valor_lote'].sum()
    
    print("Generando reporte Excel...")
    nombre_archivo = f"{PASTA_RELATORIOS}/Auditoria_{DATA_HOJE}.xlsx"
    
    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        resumo = pd.DataFrame({
            'Indicador': ['Fecha', 'Total', 'Correctos', 'Criticos', 'Vencidos', 'Valor Riesgo'],
            'Valor': [datetime.now().strftime('%d/%m/%Y %H:%M'), total_produtos, produtos_corretos, produtos_criticos, lotes_vencidos, f"R$ {valor_risco:,.2f}"]
        })
        resumo.to_excel(writer, sheet_name='Resumen', index=False)
        df_comp.to_excel(writer, sheet_name='Conciliacion', index=False)
        df_fifo.to_excel(writer, sheet_name='Lotes_FIFO', index=False)
    
    print(f"Reporte guardado: {nombre_archivo}")
    
    print("Preparando e-mail...")
    EMAIL_REMETENTE = "marcosavala236@gmail.com"
    SENHA_APP = "alntzlpsraxtzrxm"
    EMAIL_DESTINO = "soporte.savatech@gmail.com"
    
    asunto = "Auditoria Inventario - " + datetime.now().strftime('%d/%m/%Y')
    
    cuerpo_html = """<html><body style="font-family:Arial,sans-serif;">
<h2>Reporte Automatico de Inventario</h2>
<p><strong>Fecha:</strong> """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """</p>
<h3>Indicadores:</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;">
<tr style="background-color:#2E5090;color:white;"><th>Indicador</th><th>Valor</th></tr>
<tr><td>Total Productos</td><td>""" + str(total_produtos) + """</td></tr>
<tr><td>Correctos</td><td>""" + str(produtos_corretos) + """</td></tr>
<tr><td>Criticos</td><td>""" + str(produtos_criticos) + """</td></tr>
<tr><td>Lotes Vencidos</td><td>""" + str(lotes_vencidos) + """</td></tr>
<tr><td>Valor en Riesgo</td><td>R$ """ + f"{valor_risco:,.2f}" + """</td></tr>
</table>
<p><em>Sistema Multi Dados ERP</em></p>
</body></html>"""
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINO
    msg['Subject'] = Header(asunto, 'utf-8')
    msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))
    
    with open(nombre_archivo, 'rb') as archivo:
        parte = MIMEBase('application', 'octet-stream')
        parte.set_payload(archivo.read())
        encoders.encode_base64(parte)
        parte.add_header('Content-Disposition', 'attachment', filename=os.path.basename(nombre_archivo))
        msg.attach(parte)
    
    print(f"Enviando e-mail a: {EMAIL_DESTINO}...")
    servidor = smtplib.SMTP('smtp.gmail.com', 587)
    servidor.starttls()
    servidor.login(EMAIL_REMETENTE, SENHA_APP)
    servidor.send_message(msg)
    servidor.quit()
    print("E-mail enviado con exito!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
