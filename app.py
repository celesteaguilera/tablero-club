
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
from pathlib import Path

# 1. CONFIGURACION DE LA PAGINA
st.set_page_config(
    page_title="Tablero Administrativo",
    page_icon="📊",
    layout="wide"
)

BASE = Path(__file__).parent / "club.db"
CUOTA = 10000
HOY = date.today()
MES = HOY.strftime("%Y-%m")
MES_ANTERIOR = (
    HOY.replace(day=1) - timedelta(days=1)
).strftime("%Y-%m")

# 2. BASE DE DATOS
def conectar():
    return sqlite3.connect(BASE)

def iniciar_base():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS socios (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                actividad TEXT NOT NULL,
                estado TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS cuotas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                socio_id INTEGER NOT NULL,
                periodo TEXT NOT NULL,
                importe INTEGER NOT NULL,
                vencimiento TEXT NOT NULL,
                UNIQUE(socio_id, periodo),
                FOREIGN KEY(socio_id) REFERENCES socios(id)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cuota_id INTEGER NOT NULL UNIQUE,
                fecha TEXT NOT NULL,
                importe INTEGER NOT NULL,
                FOREIGN KEY(cuota_id) REFERENCES cuotas(id)
            )
        """)

        cantidad = con.execute(
            "SELECT COUNT(*) FROM socios"
        ).fetchone()[0]

        if cantidad == 0:
            socios_demo = [
                (1, "Martina Lopez", "Voley", "Activo"),
                (2, "Juan Perez", "Futbol", "Activo"),
                (3, "Lucia Fernandez", "Basquet", "Activo"),
                (4, "Tomas Gomez", "Futbol", "Activo"),
                (5, "Camila Ruiz", "Voley", "Activo"),
                (6, "Nicolas Diaz", "Basquet", "Activo"),
                (7, "Sofia Martinez", "Natacion", "Activo"),
                (8, "Mateo Garcia", "Futbol", "Activo"),
                (9, "Valentina Torres", "Natacion", "Activo"),
                (10, "Bruno Romero", "Voley", "Inactivo"),
            ]

            con.executemany(
                "INSERT OR IGNORE INTO socios (id, nombre, actividad, estado) VALUES (?, ?, ?, ?)",
                socios_demo
            )

            vencimiento_actual = (
                HOY.replace(day=1) + timedelta(days=9)
            ).isoformat()

            vencimiento_anterior = (
                date.fromisoformat(MES_ANTERIOR + "-01")
                + timedelta(days=9)
            ).isoformat()

            for socio in socios_demo:
                if socio[3] == "Activo":
                    con.execute("""
                        INSERT INTO cuotas
                        (socio_id, periodo, importe, vencimiento)
                        VALUES (?, ?, ?, ?)
                    """, (
                        socio[0], MES, CUOTA,
                        vencimiento_actual
                    ))

            for socio_id in [2, 4, 6]:
                con.execute("""
                    INSERT INTO cuotas
                    (socio_id, periodo, importe, vencimiento)
                    VALUES (?, ?, ?, ?)
                """, (
                    socio_id, MES_ANTERIOR,
                    CUOTA, vencimiento_anterior
                ))

            # Pagos ficticios iniciales
            for socio_id in [1, 3, 5, 7, 9]:
                cuota_id = con.execute("""
                    SELECT id FROM cuotas
                    WHERE socio_id = ? AND periodo = ?
                """, (socio_id, MES)).fetchone()[0]

                con.execute("""
                    INSERT INTO pagos
                    (cuota_id, fecha, importe)
                    VALUES (?, ?, ?)
                """, (cuota_id, HOY.isoformat(), CUOTA))

iniciar_base()

# Asegurar cuotas vencidas para la demostracion
with conectar() as con:
    for socio_id in [2, 4, 6]:
        periodo = "2026-09"
        vencimiento = (
            date.fromisoformat(periodo + "-01")
            + timedelta(days=9)
        ).isoformat()

        con.execute("""
            INSERT OR IGNORE INTO cuotas
            (socio_id, periodo, importe, vencimiento)
            VALUES (?, ?, ?, ?)
        """, (socio_id, periodo, CUOTA, vencimiento))

# 3. CONSULTAS
def consultar(sql, parametros=()):
    with conectar() as con:
        return pd.read_sql_query(
            sql, con, params=parametros
        )

def dinero(numero):
    return "$" + f"{int(numero):,}".replace(",", ".")

socios = consultar("SELECT * FROM socios ORDER BY nombre")

cuotas = consultar("""
    SELECT
        c.id,
        s.id AS socio_id,
        s.nombre,
        s.actividad,
        c.periodo,
        c.importe,
        c.vencimiento,
        p.fecha AS fecha_pago,
        p.importe AS pagado
    FROM cuotas c
    JOIN socios s ON s.id = c.socio_id
    LEFT JOIN pagos p ON p.cuota_id = c.id
    ORDER BY c.vencimiento, s.nombre
""")

cuotas["pendiente"] = cuotas["pagado"].isna()
cuotas["vencimiento_fecha"] = pd.to_datetime(
    cuotas["vencimiento"]
).dt.date

cuotas["vencida"] = (
    cuotas["pendiente"]
    & (cuotas["vencimiento_fecha"] < HOY)
)

cuotas["dias_atraso"] = cuotas["vencimiento_fecha"].apply(
    lambda d: max((HOY - d).days, 0)
)

cuotas["estado"] = cuotas.apply(
    lambda fila: (
        "Pagada" if not fila["pendiente"]
        else "Vencida" if fila["vencida"]
        else "Pendiente"
    ),
    axis=1
)

# 4. ESTILO
st.markdown("""
<style>
.stApp {
    background-color: #fff9fb;
}
h1, h2, h3 {
    color: #781c45;
}
div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #f1d5e0;
    border-radius: 14px;
    padding: 16px;
}
section[data-testid="stSidebar"] {
    background-color: #f7e8ee;
}
</style>
""", unsafe_allow_html=True)

# 5. MENU
st.sidebar.title("Gestion Administrativa")
st.sidebar.caption("Proyecto Grupo F")
st.sidebar.caption("Prototipo con datos ficticios")

pagina = st.sidebar.radio(
    "Navegacion",
    [
        "Resumen general",
        "Socios",
        "Cuotas",
        "Actividades"
    ]
)

st.title("Tablero Administrativo")
st.caption(
    "Socios, cuotas y actividades en una sola pantalla"
)
st.info("Demostracion educativa con datos ficticios.")

# 6. INDICADORES
activos = socios[socios["estado"] == "Activo"]
socios_activos = len(activos)

cuotas_vencidas = int(cuotas["vencida"].sum())

pagos_mes = cuotas[
    cuotas["fecha_pago"].fillna("").str.startswith(MES)
]
recaudacion = int(pagos_mes["pagado"].sum())

pendiente_mes = cuotas[
    (cuotas["periodo"] == MES)
    & cuotas["pendiente"]
]
total_pendiente = int(pendiente_mes["importe"].sum())

inscriptos = len(activos)

# VISTA 1: RESUMEN GENERAL
if pagina == "Resumen general":
    st.header("📊 Resumen general")

    a, b, c, d, e = st.columns([1, 1, 1.5, 1.5, 1])

    a.metric("Socios activos", socios_activos)
    b.metric("Cuotas vencidas", cuotas_vencidas)
    c.metric("Recaudado este mes", dinero(recaudacion))
    deuda_total = int(cuotas.loc[cuotas["pendiente"], "importe"].sum())
    d.metric("Deuda total pendiente", dinero(deuda_total))
    e.metric("Inscriptos", inscriptos)

    st.divider()

    izquierda, derecha = st.columns(2)

    with izquierda:
        st.subheader("Socios por actividad")
        conteo = activos["actividad"].value_counts()
        st.bar_chart(conteo)

    with derecha:
        st.subheader("Estado de las cuotas")
        estados = cuotas["estado"].value_counts()
        st.bar_chart(estados)

    st.subheader("Deudas vencidas")
    vencidas = cuotas[cuotas["vencida"]].copy()

    if vencidas.empty:
        st.success("No hay cuotas vencidas.")
    else:
        st.dataframe(
            vencidas[
                ["nombre", "periodo", "importe",
                 "dias_atraso", "estado"]
            ],
            hide_index=True,
            use_container_width=True
        )

# VISTA 2: SOCIOS
elif pagina == "Socios":
    st.header("👥 Padron de socios")

    busqueda = st.text_input(
        "Buscar socio por nombre"
    )

    actividades = sorted(
        socios["actividad"].unique().tolist()
    )

    filtro_actividad = st.selectbox(
        "Filtrar por actividad",
        ["Todas"] + actividades
    )

    filtro_estado = st.selectbox(
        "Estado del socio",
        ["Todos", "Activo", "Inactivo"]
    )

    resultado = socios.copy()

    if busqueda:
        resultado = resultado[
            resultado["nombre"].str.contains(
                busqueda, case=False, regex=False
            )
        ]

    if filtro_actividad != "Todas":
        resultado = resultado[
            resultado["actividad"] == filtro_actividad
        ]

    if filtro_estado != "Todos":
        resultado = resultado[
            resultado["estado"] == filtro_estado
        ]

    st.write(f"Socios encontrados: {len(resultado)}")

    st.dataframe(
        resultado,
        hide_index=True,
        use_container_width=True
    )

    st.download_button(
        "Descargar padron CSV",
        resultado.to_csv(index=False).encode("utf-8-sig"),
        file_name="socios_club.csv",
        mime="text/csv"
    )

# VISTA 3: CUOTAS
elif pagina == "Cuotas":
    st.header("💰 Control de cuotas")

    st.subheader("Consultar deudas")

    estado_filtro = st.selectbox(
        "Filtrar cuotas",
        ["Todas", "Vencida", "Pendiente", "Pagada"]
    )

    resultado = cuotas.copy()

    if estado_filtro != "Todas":
        resultado = resultado[
            resultado["estado"] == estado_filtro
        ]

    st.dataframe(
        resultado[
            ["nombre", "actividad", "periodo",
             "importe", "estado", "dias_atraso"]
        ],
        hide_index=True,
        use_container_width=True
    )

    st.divider()
    st.subheader("Registrar un pago")

    disponibles = cuotas[cuotas["pendiente"]].copy()

    if disponibles.empty:
        st.success("Todas las cuotas estan pagadas.")
    else:
        disponibles["etiqueta"] = disponibles.apply(
            lambda f: (
                f"{f['nombre']} | {f['periodo']} | "
                f"{dinero(f['importe'])}"
            ),
            axis=1
        )

        opciones = dict(zip(
            disponibles["etiqueta"],
            disponibles["id"]
        ))

        with st.form("formulario_pago"):
            seleccion = st.selectbox(
                "Seleccionar cuota pendiente",
                list(opciones.keys())
            )

            fecha_pago = st.date_input(
                "Fecha del pago",
                value=HOY,
                max_value=HOY
            )

            confirmar = st.form_submit_button(
                "Registrar pago"
            )

        if confirmar:
            cuota_id = int(opciones[seleccion])

            importe = int(
                disponibles.loc[
                    disponibles["id"] == cuota_id,
                    "importe"
                ].iloc[0]
            )

            try:
                with conectar() as con:
                    con.execute("""
                        INSERT INTO pagos
                        (cuota_id, fecha, importe)
                        VALUES (?, ?, ?)
                    """, (
                        cuota_id,
                        fecha_pago.isoformat(),
                        importe
                    ))

                st.success(
                    "Pago registrado correctamente."
                )
                st.rerun()

            except sqlite3.IntegrityError:
                st.error(
                    "Esta cuota ya tiene un pago registrado."
                )

    st.divider()
    st.subheader("Historial de pagos")

    historial = consultar("""
        SELECT
            s.nombre,
            c.periodo,
            p.fecha,
            p.importe
        FROM pagos p
        JOIN cuotas c ON c.id = p.cuota_id
        JOIN socios s ON s.id = c.socio_id
        ORDER BY p.fecha DESC, p.id DESC
    """)

    st.dataframe(
        historial,
        hide_index=True,
        use_container_width=True
    )

    st.download_button(
        "Descargar historial CSV",
        historial.to_csv(index=False).encode("utf-8-sig"),
        file_name="pagos_club.csv",
        mime="text/csv"
    )

# VISTA 4: ACTIVIDADES
elif pagina == "Actividades":
    st.header("⚽ Actividades deportivas")

    cupos = {
        "Futbol": 20,
        "Voley": 15,
        "Basquet": 15,
        "Natacion": 10
    }

    resumen = []

    for actividad, cupo in cupos.items():
        cantidad = len(
            activos[activos["actividad"] == actividad]
        )

        resumen.append({
            "Actividad": actividad,
            "Inscriptos": cantidad,
            "Cupo": cupo,
            "Disponibles": max(cupo - cantidad, 0)
        })

    tabla = pd.DataFrame(resumen)

    st.dataframe(
        tabla,
        hide_index=True,
        use_container_width=True
    )

    st.subheader("Inscriptos por deporte")
    st.bar_chart(
        tabla.set_index("Actividad")[
            ["Inscriptos", "Cupo"]
        ]
    )

    actividad_elegida = st.selectbox(
        "Ver inscriptos de",
        list(cupos.keys())
    )

    st.dataframe(
        activos[
            activos["actividad"] == actividad_elegida
        ][["nombre", "actividad"]],
        hide_index=True,
        use_container_width=True
    )

st.divider()
st.caption(
    "Grupo F | Prototipo funcional educativo | "
    "Datos ficticios"
)
