#!/bin/bash

echo "🚀 Creando estructura del Portafolio Savatech Dados..."

mkdir -p Portafolio-Savatech-Dados/{src/{dashboard,automatizacion,analisis},docs/{propuestas,acuerdos,arquitectura},assets/{imagenes,capturas,diagramas},datos}

cd Portafolio-Savatech-Dados

touch README.md requirements.txt .gitignore
touch src/dashboard/dashboard_web.py
touch src/automatizacion/automatizacion_inventario.py
touch src/analisis/{conciliador_inventario.py,analisis_fifo.py,acciones_correctivas.py}
touch docs/propuestas/propuesta-comercial.md
touch docs/acuerdos/acuerdo-piloto-15dias.md
touch docs/arquitectura/integracion-erp.md

echo "✅ ¡Estructura creada exitosamente!"
tree -L 2
