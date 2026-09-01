
"""
SolarCalc Paraguay - Calculadora de Consumo Eléctrico y Dimensionamiento Solar
Para Asunción, Paraguay
Ejecutar con: streamlit run app.py
"""

import streamlit as st
import pandas as pd

# =============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# =============================================================================
st.set_page_config(
    page_title="SolarCalc Paraguay",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CONSTANTES Y PARÁMETROS TÉCNICOS
# =============================================================================

# Parámetros solares para Asunción, Paraguay
IRRADIACION_PROMEDIO = 4.85       # kWh/m²/día (promedio anual sólido)
POTENCIA_PANEL = 600              # W nominales por panel
PERFORMANCE_RATIO = 0.78          # Factor de pérdidas del sistema
DIAS_MES = 30

# Parámetros de baterías
BATERIA_VOLT = 12                 # V
BATERIA_AH = 200                  # Ah
BATERIA_PRECIO_GS = 2_880_000     # Gs por unidad (ya en guaraníes)
BATERIAS_POR_INVERSOR = 4

# Precios en USD (antes de IVA)
PRECIO_PANEL_USD = 125
PRECIO_INVERSOR_USD = 355
IVA = 0.10                        # 10% IVA en Paraguay
TIPO_CAMBIO = 6000                # 1 USD = 6.000 Gs

# Potencias típicas de electrodomésticos (W)
POTENCIA_HELADERA = {"Chica": 120, "Mediana": 180, "Grande": 250}
POTENCIA_LAMPARA_LED = 9          # W promedio
POTENCIA_LAMPARA_CONV = 60        # W promedio (incandescente/halógena)
POTENCIA_COCINA = 2000            # W promedio
POTENCIA_HORNO = 1500             # W promedio

# Aire acondicionado: COP típico inverter ~3.5
COP_INVERTER = 3.5

def btu_a_kw(btu):
    """Convierte BTU/hr a kW de consumo eléctrico real considerando COP."""
    capacidad_w = btu * 0.293
    consumo_w = capacidad_w / COP_INVERTER
    return consumo_w / 1000

# =============================================================================
# ESTILOS CSS PERSONALIZADOS
# =============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a5276;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #5d6d7e;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #2874a6;
        border-bottom: 2px solid #2874a6;
        padding-bottom: 0.3rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #2874a6;
    }
    .highlight-box {
        background-color: #eaf2f8;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #aed6f1;
    }
    .note-box {
        background-color: #fef9e7;
        border-radius: 8px;
        padding: 0.8rem;
        border-left: 4px solid #f4d03f;
        font-size: 0.9rem;
        color: #7d6608;
    }
    .result-box {
        background-color: #e8f8f5;
        border-radius: 10px;
        padding: 1.2rem;
        border: 2px solid #1abc9c;
    }
    .cost-box {
        background-color: #fdedec;
        border-radius: 10px;
        padding: 1.2rem;
        border: 2px solid #e74c3c;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def formato_gs(valor):
    """Formatea un número en guaraníes con separador de miles."""
    return f"Gs {valor:,.0f}".replace(",", ".")

def calcular_consumo_heladera(tamano, horas_dia=24):
    """Heladera: ciclo de encendido ~8 horas efectivas al día promedio."""
    potencia = POTENCIA_HELADERA[tamano]
    factor_ciclo = 0.35
    kwh_dia = (potencia / 1000) * 24 * factor_ciclo
    return kwh_dia

def calcular_consumo_aire(btu, horas_dia):
    """Consumo diario de aire acondicionado en kWh."""
    kw = btu_a_kw(btu)
    return kw * horas_dia

def calcular_consumo_iluminacion(cantidad, tecnologia, horas_dia):
    """Consumo diario de iluminación en kWh."""
    potencia = POTENCIA_LAMPARA_LED if tecnologia == "LED" else POTENCIA_LAMPARA_CONV
    return (potencia * cantidad / 1000) * horas_dia

def calcular_consumo_cocina(horas_dia):
    """Consumo diario de cocina eléctrica en kWh."""
    return (POTENCIA_COCINA / 1000) * horas_dia

def calcular_consumo_horno(horas_dia):
    """Consumo diario de horno eléctrico en kWh."""
    return (POTENCIA_HORNO / 1000) * horas_dia

# =============================================================================
# INICIALIZACIÓN DE SESSION STATE
# =============================================================================
if "hel_pot" not in st.session_state:
    st.session_state.hel_pot = 120
if "otros" not in st.session_state:
    st.session_state.otros = []

# =============================================================================
# CALLBACKS
# =============================================================================
def update_heladera_pot():
    """Callback para actualizar la potencia de la heladera según el tamaño seleccionado."""
    tamano = st.session_state.hel_tam
    if tamano == "Chica":
        st.session_state.hel_pot = 120
    elif tamano == "Mediana":
        st.session_state.hel_pot = 180
    else:
        st.session_state.hel_pot = 250

def agregar_otro():
    """Callback para agregar un electrodoméstico personalizado."""
    nombre = st.session_state.get("nombre_otro", "").strip()
    potencia = st.session_state.get("pot_otro", 0)
    horas = st.session_state.get("hrs_otro", 0.0)
    if nombre and potencia > 0:
        st.session_state.otros.append({"nombre": nombre, "potencia": potencia, "horas": horas})
        # Limpiar campos
        st.session_state.nombre_otro = ""
        st.session_state.pot_otro = 100
        st.session_state.hrs_otro = 4.0

def eliminar_otro(idx):
    """Callback para eliminar un electrodoméstico personalizado."""
    if 0 <= idx < len(st.session_state.otros):
        st.session_state.otros.pop(idx)

# =============================================================================
# ENCABEZADO
# =============================================================================
st.markdown('<div class="main-header">☀️ SolarCalc Paraguay</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Calculadora de Consumo Eléctrico y Dimensionamiento Solar para Asunción</div>', unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# SECCIÓN 1: CARGA DE ELECTRODOMÉSTICOS
# =============================================================================
st.markdown('<div class="section-title">📋 1. Carga de Electrodomésticos</div>', unsafe_allow_html=True)

# Inicializar lista de consumos
consumos = []

# --- Heladera ---
with st.expander("❄️ Heladera", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        heladera_tamano = st.selectbox(
            "Tamaño de la heladera",
            ["Chica", "Mediana", "Grande"],
            key="hel_tam",
            on_change=update_heladera_pot
        )
    with col2:
        heladera_pot = st.number_input(
            "Potencia asignada (W)",
            value=st.session_state.hel_pot,
            key="hel_pot"
        )

    kwh_heladera = calcular_consumo_heladera(heladera_tamano)
    consumos.append({
        "Electrodoméstico": f"Heladera ({heladera_tamano})",
        "kWh/día": kwh_heladera,
        "kWh/mes": kwh_heladera * DIAS_MES
    })
    st.info(f"Consumo estimado: **{kwh_heladera:.2f} kWh/día** | **{kwh_heladera * DIAS_MES:.2f} kWh/mes** (factor de ciclo ~35%)")

# --- Aire Acondicionado ---
with st.expander("🌬️ Aire Acondicionado (hasta 3 equipos)", expanded=True):
    num_aires = st.number_input("Cantidad de equipos de aire", min_value=0, max_value=3, value=1, step=1, key="num_aires")

    for i in range(num_aires):
        st.markdown(f"**Equipo {i+1}**")
        cols = st.columns(3)
        with cols[0]:
            btu = st.selectbox(f"BTU/hr - Equipo {i+1}", [9000, 12000, 18000, 24000, 30000, 36000], key=f"btu_{i}")
        with cols[1]:
            horas_aire = st.number_input(f"Horas de uso/día - Equipo {i+1}", min_value=0.0, max_value=24.0, value=6.0, step=0.5, key=f"hrs_aire_{i}")
        with cols[2]:
            kw_real = btu_a_kw(btu)
            st.metric("Potencia eléctrica", f"{kw_real:.2f} kW", help=f"COP inverter = {COP_INVERTER}")

        kwh_aire = calcular_consumo_aire(btu, horas_aire)
        consumos.append({
            "Electrodoméstico": f"Aire Acond. {i+1} ({btu:,} BTU)",
            "kWh/día": kwh_aire,
            "kWh/mes": kwh_aire * DIAS_MES
        })

# --- Iluminación ---
with st.expander("💡 Iluminación", expanded=True):
    cols = st.columns(4)
    with cols[0]:
        cant_lamparas = st.number_input("Cantidad de lámparas", min_value=0, value=10, step=1, key="num_lamp")
    with cols[1]:
        tec_lamp = st.selectbox("Tecnología", ["LED", "Convencional"], key="tec_lamp")
    with cols[2]:
        pot_lamp = POTENCIA_LAMPARA_LED if tec_lamp == "LED" else POTENCIA_LAMPARA_CONV
        st.metric("Potencia/lámpara", f"{pot_lamp} W")
    with cols[3]:
        horas_luz = st.number_input("Horas de uso/día", min_value=0.0, max_value=24.0, value=5.0, step=0.5, key="hrs_luz")

    kwh_luz = calcular_consumo_iluminacion(cant_lamparas, tec_lamp, horas_luz)
    consumos.append({
        "Electrodoméstico": f"Iluminación ({cant_lamparas} x {tec_lamp})",
        "kWh/día": kwh_luz,
        "kWh/mes": kwh_luz * DIAS_MES
    })

# --- Cocina Eléctrica ---
with st.expander("🍳 Cocina Eléctrica", expanded=False):
    horas_cocina = st.number_input("Horas de uso al día", min_value=0.0, max_value=24.0, value=1.5, step=0.5, key="hrs_cocina")
    kwh_cocina = calcular_consumo_cocina(horas_cocina)
    consumos.append({
        "Electrodoméstico": "Cocina Eléctrica",
        "kWh/día": kwh_cocina,
        "kWh/mes": kwh_cocina * DIAS_MES
    })

# --- Horno Eléctrico ---
with st.expander("🔥 Horno Eléctrico", expanded=False):
    horas_horno = st.number_input("Horas de uso al día", min_value=0.0, max_value=24.0, value=0.5, step=0.5, key="hrs_horno")
    kwh_horno = calcular_consumo_horno(horas_horno)
    consumos.append({
        "Electrodoméstico": "Horno Eléctrico",
        "kWh/día": kwh_horno,
        "kWh/mes": kwh_horno * DIAS_MES
    })

# --- Otros Electrodomésticos ---
with st.expander("➕ Otros Electrodomésticos", expanded=False):
    st.markdown("Agrega electrodomésticos adicionales (nombre, potencia en W, horas de uso diarias)")

    col_n, col_p, col_h, col_b = st.columns([3, 2, 2, 1])
    with col_n:
        st.text_input("Nombre", key="nombre_otro", placeholder="Ej: TV, lavarropas...")
    with col_p:
        st.number_input("Potencia (W)", min_value=0, value=100, step=10, key="pot_otro")
    with col_h:
        st.number_input("Horas/día", min_value=0.0, max_value=24.0, value=4.0, step=0.5, key="hrs_otro")
    with col_b:
        st.write("")
        st.write("")
        st.button("➕ Agregar", key="btn_agregar", on_click=agregar_otro)

    # Mostrar lista de otros
    if st.session_state.otros:
        for idx, item in enumerate(st.session_state.otros):
            kwh_otro = (item["potencia"] / 1000) * item["horas"]
            consumos.append({
                "Electrodoméstico": item["nombre"],
                "kWh/día": kwh_otro,
                "kWh/mes": kwh_otro * DIAS_MES
            })
            cols = st.columns([4, 1])
            with cols[0]:
                st.write(f"• **{item['nombre']}** — {item['potencia']} W × {item['horas']} h/día = {kwh_otro:.2f} kWh/día")
            with cols[1]:
                st.button("🗑️", key=f"del_{idx}", on_click=eliminar_otro, args=(idx,))

# =============================================================================
# SECCIÓN 2: RESUMEN DE CONSUMO
# =============================================================================
st.markdown("---")
st.markdown('<div class="section-title">📊 2. Resumen de Consumo Eléctrico</div>', unsafe_allow_html=True)

df_consumos = pd.DataFrame(consumos)
if not df_consumos.empty:
    total_kwh_dia = df_consumos["kWh/día"].sum()
    total_kwh_mes = df_consumos["kWh/mes"].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Consumo Diario", f"{total_kwh_dia:.2f} kWh")
    with col2:
        st.metric("Consumo Mensual", f"{total_kwh_mes:.2f} kWh")
    with col3:
        st.metric("Consumo Anual", f"{total_kwh_mes * 12:.2f} kWh")

    st.markdown("#### Detalle por electrodoméstico")
    df_display = df_consumos.copy()
    df_display["kWh/día"] = df_display["kWh/día"].round(2)
    df_display["kWh/mes"] = df_display["kWh/mes"].round(2)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ No hay electrodomésticos cargados.")
    total_kwh_dia = 0
    total_kwh_mes = 0

# =============================================================================
# SECCIÓN 3: COSTO DE LA ENERGÍA
# =============================================================================
st.markdown("---")
st.markdown('<div class="section-title">💰 3. Costo de la Energía (ANDE)</div>', unsafe_allow_html=True)

st.markdown('<div class="note-box">💡 El valor por defecto corresponde a la tarifa residencial típica de ANDE. Puedes ajustarlo según tu factura actual.</div>', unsafe_allow_html=True)
st.write("")

costo_kwh = st.number_input(
    "Costo del kWh (Guaraníes)",
    min_value=0,
    value=330,
    step=10,
    help="Tarifa residencial típica de ANDE en Paraguay"
)

costo_mensual = total_kwh_mes * costo_kwh

col1, col2 = st.columns(2)
with col1:
    st.metric("Costo del kWh", f"Gs {costo_kwh}")
with col2:
    st.metric("Costo mensual estimado", formato_gs(costo_mensual))

# =============================================================================
# SECCIÓN 4: SELECCIÓN DE SISTEMA SOLAR
# =============================================================================
st.markdown("---")
st.markdown('<div class="section-title">🔆 4. Selección del Sistema Solar</div>', unsafe_allow_html=True)

st.markdown("""
<div class="highlight-box">
<strong>Opción 1 – Sistema con baterías (24/7):</strong> Genera energía de día, almacena en baterías para la noche. El excedente se vierte a la red de ANDE.<br><br>
<strong>Opción 2 – Sistema sin baterías (solo diurno):</strong> Genera energía solo durante las horas de sol. El excedente se vierte a la red de ANDE. No incluye almacenamiento.
</div>
""", unsafe_allow_html=True)
st.write("")

opcion_sistema = st.radio(
    "Selecciona el tipo de sistema:",
    ["Opción 1: Con baterías (cobertura 24/7)", "Opción 2: Sin baterías (solo diurno)"],
    horizontal=True
)

con_baterias = opcion_sistema.startswith("Opción 1")

# =============================================================================
# SECCIÓN 5: DIMENSIONAMIENTO SOLAR
# =============================================================================
st.markdown("---")
st.markdown('<div class="section-title">📐 5. Resultados del Dimensionamiento Solar</div>', unsafe_allow_html=True)

st.markdown(f'<div class="note-box">🌤️ Irradiación solar promedio en Asunción: <strong>{IRRADIACION_PROMEDIO} kWh/m²/día</strong> | Performance Ratio del sistema: <strong>{PERFORMANCE_RATIO*100:.0f}%</strong> | Paneles de <strong>{POTENCIA_PANEL} W</strong></div>', unsafe_allow_html=True)
st.write("")

if total_kwh_dia > 0:
    # --- Cálculos de paneles ---
    energia_necesaria_dia = total_kwh_dia / PERFORMANCE_RATIO
    num_paneles = int(energia_necesaria_dia / (POTENCIA_PANEL / 1000 * IRRADIACION_PROMEDIO)) + 1
    potencia_total_kw = (num_paneles * POTENCIA_PANEL) / 1000
    energia_generada_dia = num_paneles * (POTENCIA_PANEL / 1000) * IRRADIACION_PROMEDIO * PERFORMANCE_RATIO
    energia_generada_mes = energia_generada_dia * DIAS_MES

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Energía necesaria/día", f"{energia_necesaria_dia:.2f} kWh", help="Incluye pérdidas del sistema")
    with col2:
        st.metric("Paneles 600W necesarios", f"{num_paneles} unidades")
    with col3:
        st.metric("Potencia total del sistema", f"{potencia_total_kw:.2f} kW")

    st.markdown("---")

    # --- Paneles: detalle ---
    st.markdown("#### 📦 Detalle de Paneles Solares")
    precio_panel_usd_iva = PRECIO_PANEL_USD * (1 + IVA)
    precio_panel_gs = precio_panel_usd_iva * TIPO_CAMBIO
    costo_paneles_total = num_paneles * precio_panel_gs

    cols = st.columns(3)
    with cols[0]:
        st.metric("Precio unitario (con IVA)", formato_gs(precio_panel_gs))
    with cols[1]:
        st.metric("Cantidad", f"{num_paneles} paneles")
    with cols[2]:
        st.metric("Inversión en paneles", formato_gs(costo_paneles_total))

    # --- Inversor ---
    st.markdown("#### 🔌 Inversor")
    precio_inv_usd_iva = PRECIO_INVERSOR_USD * (1 + IVA)
    precio_inv_gs = precio_inv_usd_iva * TIPO_CAMBIO

    cols = st.columns(3)
    with cols[0]:
        st.metric("Modelo", "5.000 W")
    with cols[1]:
        st.metric("Precio unitario (con IVA)", formato_gs(precio_inv_gs))
    with cols[2]:
        st.metric("Inversión en inversor", formato_gs(precio_inv_gs))

    # --- Baterías (solo Opción 1) ---
    if con_baterias:
        st.markdown("#### 🔋 Baterías")

        DoD = 0.50
        capacidad_bateria_kwh = (BATERIA_VOLT * BATERIA_AH / 1000) * DoD
        energia_almacenar = total_kwh_dia

        num_baterias = max(BATERIAS_POR_INVERSOR, int(energia_almacenar / capacidad_bateria_kwh) + 1)
        if num_baterias % 4 != 0:
            num_baterias = ((num_baterias // 4) + 1) * 4

        capacidad_total_kwh = num_baterias * capacidad_bateria_kwh
        costo_baterias_total = num_baterias * BATERIA_PRECIO_GS

        cols = st.columns(4)
        with cols[0]:
            st.metric("Modelo", f"{BATERIA_VOLT}V {BATERIA_AH}Ah")
        with cols[1]:
            st.metric("Capacidad útil/batería", f"{capacidad_bateria_kwh:.2f} kWh", help=f"DoD = {DoD*100:.0f}%")
        with cols[2]:
            st.metric(f"Cantidad ({num_baterias//4} string × 4)", f"{num_baterias} unidades")
        with cols[3]:
            st.metric("Capacidad total útil", f"{capacidad_total_kwh:.2f} kWh")

        st.metric("Inversión en baterías", formato_gs(costo_baterias_total))

        st.markdown(f'<div class="note-box">🔋 Configuración: {num_baterias//4} strings de 4 baterías en serie (48V) | Autonomía: ~{capacidad_total_kwh/total_kwh_dia:.1f} días</div>', unsafe_allow_html=True)
    else:
        num_baterias = 0
        costo_baterias_total = 0
        capacidad_total_kwh = 0

    # =============================================================================
    # SECCIÓN 6: CÁLCULO ECONÓMICO
    # =============================================================================
    st.markdown("---")
    st.markdown('<div class="section-title">💵 6. Análisis Económico</div>', unsafe_allow_html=True)

    inversion_total = costo_paneles_total + precio_inv_gs + costo_baterias_total
    ahorro_mensual = min(energia_generada_mes, total_kwh_mes) * costo_kwh

    if ahorro_mensual > 0:
        roi_meses = inversion_total / ahorro_mensual
        roi_anos = roi_meses / 12
    else:
        roi_meses = float('inf')
        roi_anos = float('inf')

    # Tabla resumen de inversión
    st.markdown("#### 📋 Desglose de Inversión Inicial")

    data_inversion = [
        ["Paneles Solares (600W)", f"{num_paneles} unidades", formato_gs(costo_paneles_total)],
        ["Inversor", "1 unidad (5.000 W)", formato_gs(precio_inv_gs)],
    ]
    if con_baterias:
        data_inversion.append(["Baterías", f"{num_baterias} unidades ({BATERIA_VOLT}V {BATERIA_AH}Ah)", formato_gs(costo_baterias_total)])
    data_inversion.append(["TOTAL INVERSIÓN", "", f"**{formato_gs(inversion_total)}**"])

    df_inversion = pd.DataFrame(data_inversion, columns=["Concepto", "Cantidad", "Monto (Gs)"])
    st.table(df_inversion)

    # Métricas principales
    st.markdown("---")
    st.markdown("#### 📈 Métricas de Retorno de Inversión")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Inversión Total", formato_gs(inversion_total))
    with col2:
        st.metric("Ahorro Mensual", formato_gs(ahorro_mensual))
    with col3:
        if roi_meses != float('inf'):
            st.metric("Payback (meses)", f"{roi_meses:.1f}")
        else:
            st.metric("Payback (meses)", "∞")
    with col4:
        if roi_anos != float('inf'):
            st.metric("Payback (años)", f"{roi_anos:.1f}")
        else:
            st.metric("Payback (años)", "∞")

    # Gráfico de payback acumulado
    st.markdown("#### 📉 Evolución del Ahorro Acumulado")

    if roi_meses != float('inf'):
        meses_grafico = list(range(0, int(roi_meses) + 24))
    else:
        meses_grafico = list(range(0, 61))
    ahorro_acumulado = [m * ahorro_mensual for m in meses_grafico]

    df_payback = pd.DataFrame({
        "Mes": meses_grafico,
        "Ahorro Acumulado (Gs)": ahorro_acumulado,
        "Inversión Inicial (Gs)": [inversion_total] * len(meses_grafico)
    })

    st.line_chart(df_payback.set_index("Mes"), use_container_width=True)

    # Resumen final
    st.markdown("---")
    st.markdown('<div class="result-box">', unsafe_allow_html=True)
    st.markdown(f"""
    ### ✅ Resumen del Sistema Recomendado

    | Concepto | Valor |
    |----------|-------|
    | **Tipo de sistema** | {'Con baterías (24/7)' if con_baterias else 'Sin baterías (solo diurno)'} |
    | **Consumo mensual estimado** | {total_kwh_mes:.2f} kWh |
    | **Paneles solares** | {num_paneles} × 600 W = {potencia_total_kw:.2f} kW |
    | **Energía generada/mes** | {energia_generada_mes:.2f} kWh |
    | **Inversión total** | {formato_gs(inversion_total)} |
    | **Ahorro mensual** | {formato_gs(ahorro_mensual)} |
    | **Payback period** | {roi_meses:.1f} meses ({roi_anos:.1f} años) |
    """)
    if con_baterias:
        st.markdown(f"| **Baterías** | {num_baterias} × {BATERIA_VOLT}V {BATERIA_AH}Ah ({capacidad_total_kwh:.2f} kWh útiles) |")
    st.markdown('</div>', unsafe_allow_html=True)

    # Notas finales
    st.markdown("---")
    st.markdown(f'<div class="note-box">📌 <strong>Notas importantes:</strong><br>• Los valores de irradiación solar ({IRRADIACION_PROMEDIO} kWh/m²/día) y rendimiento son promedios estimados para Asunción, Paraguay.<br>• El Performance Ratio del sistema ({PERFORMANCE_RATIO*100:.0f}%) considera pérdidas por temperatura, cableado, inversor, suciedad y envejecimiento.<br>• Los precios son referenciales y pueden variar según proveedor y condiciones del mercado.<br>• Se recomienda consultar con un instalador certificado para un dimensionamiento preciso en sitio.<br>• La ANDE permite el vertimiento de excedentes mediante el mecanismo de net metering.</div>', unsafe_allow_html=True)

else:
    st.warning("⚠️ Carga al menos un electrodoméstico para ver el dimensionamiento solar.")

# =============================================================================
# PIE DE PÁGINA
# =============================================================================
st.markdown("---")
st.markdown("<div style='text-align:center; color:#7f8c8d; font-size:0.85rem;'>☀️ SolarCalc Paraguay — Calculadora de referencia para dimensionamiento solar en Asunción</div>", unsafe_allow_html=True)
