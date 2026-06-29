cat > README.md << 'EOF'
# Sistema de Inteligência de Inventários - Savatech Dados ERP

## 🎯 Descrição do Projeto
Módulo de Business Intelligence projetado para integrar-se a ERPs do setor varejista (supermercados).
O sistema automatiza a conciliação de inventários, detecta vazamentos de mercadorias (roubos/perdas)
em tempo real e alerta sobre lotes próximos ao vencimento utilizando o método FIFO.

## 📊 Problema de Negócio Resolvido
Os supermercados perdem entre 2% e 4% de seu faturamento anual por "perdas invisíveis":
- Roubos formiga não detectados
- Erros no recebimento de mercadorias
- Produtos vencidos na prateleira
- Diferenças entre estoque físico e de sistema

## ✨ Características Principais

### 1. Auditoria Automática Diária
- Cruzamento automático entre inventário físico e de sistema
- Detecção de discrepâncias em tempo real
- Alertas por e-mail com KPIs e relatórios anexos

### 2. Radar de Vencimentos FIFO
- Alertas precoces de lotes próximos ao vencimento
- Visualização interativa por dias restantes
- Integração com método FIFO (First In, First Out)

### 3. Dashboard Executivo Interativo
- Painel web desenvolvido em Streamlit
- Gráficos dinâmicos com Plotly
- Filtros por categoria, estado e período
- Download de dados em CSV/Excel

### 4. Automação de Relatórios
- Envio automático de e-mails diários (8:00 AM)
- Excel com formatação condicional e cores
- Plano de ações corretivas com responsáveis

## 🛠️ Stack Tecnológico
- **Backend:** Python 3.14, Pandas, SQLite
- **Frontend:** Streamlit, Plotly
- **Automação:** SMTP, Cron Jobs
- **Visualização:** Matplotlib, Plotly

## 📈 Resultados Esperados
- **Detecção de vazamentos:** Identificação de 40% de produtos com discrepâncias críticas
- **Redução de perdas:** Alertas precoces de vencimentos
- **Economia de tempo:** 15+ horas semanais de trabalho manual
- **ROI:** O sistema se paga sozinho nos primeiros 15 dias

## 🚀 Instalação e Uso

### Requisitos
```bash
pip install -r requirements.txt