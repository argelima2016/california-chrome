c_cerrada_actual = st.session_state.carreras_cerradas_remate.get(carr_seleccionada_liq, False)
    
    if c_cerrada_actual:
        st.error(f"🔴 {carr_seleccionada_liq} se encuentra CERRADA")
        if st.button("🔓 Reabrir Remates de la Carrera", key=f"sb_reabrir_{carr_seleccionada_liq}"):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = False
            st.success(f"Se reabrieron las pujas para {carr_seleccionada_liq}")
            st.rerun()
    else:
        st.success(f"🟢 {carr_seleccionada_liq} se encuentra ABIERTA")
        if st.button("🔒 Cerrar Definitivamente Carrera", key=f"sb_cerrar_{carr_seleccionada_liq}"):
            st.session_state.carreras_cerradas_remate[carr_seleccionada_liq] = True
            st.warning(f"Se cerraron las pujas para {carr_seleccionada_liq}")
            st.rerun()

    st.markdown("---")
    st.subheader("🏆 Cargar Ganador y Liquidar")
    
    lista_ejemplares_liq = st.session_state.banco_caballos_por_carrera.get(carr_seleccionada_liq, [])
    if lista_ejemplares_liq:
        ganador_seleccionado = st.selectbox("Seleccionar Ejemplar Ganador", lista_ejemplares_liq, key="sb_liq_sel_ganador")
        
        if st.button("💰 Liquidar Premio a Ganador", key="sb_btn_liquidar"):
            info_ganador = st.session_state.remates[carr_seleccionada_liq].get(ganador_seleccionado, {"jugador": "Sin Postor", "monto": 0.0})
            comprador = info_ganador["jugador"]
            
            # Cálculo del pozo total acumulado en la carrera
            pozo_total = sum(datos["monto"] for datos in st.session_state.remates[carr_seleccionada_liq].values())
            inc = st.session_state.detalles_carreras[carr_seleccionada_liq].get("incentivo", 0.0)
            pozo_total_con_incentivo = pozo_total + inc
            
            retencion = (porcentaje_casa / 100.0) * pozo_total
            premio_neto = pozo_total_con_incentivo - retencion
            
            if comprador != "Sin Postor":
                if comprador not in st.session_state.cuentas:
                    st.session_state.cuentas[comprador] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                
                # Asignación del premio al comprador
                st.session_state.cuentas[comprador]['Premios'] += premio_neto
                st.session_state.ganancia_casa += retencion
                st.session_state.historial_ganadores[carr_seleccionada_liq] = {
                    "ejemplar": ganador_seleccionado,
                    "ganador": comprador,
                    "premio": premio_neto
                }
                st.success(f"¡Premio de {formatear_bs(premio_neto)} acreditado con éxito a {comprador}!")
                st.rerun()
            else:
                st.error("El ejemplar ganador no tuvo postor. El pozo pasa a la CASA.")


# ==============================================================================
# SECCIÓN PRINCIPAL SEGÚN OPCIÓN SELECCIONADA EN EL MENÚ
# ==============================================================================

# ------------------------------------------------------------------------------
# OPCIÓN 1: REMATES
# ------------------------------------------------------------------------------
if st.session_state.menu_principal_opcion == "Remates":
    
    col_sub1, col_sub2, col_sub3 = st.columns(3, gap="small")
    with col_sub1:
        if st.button("EN VIVO", key="btn_sub_envivo", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "En Vivo" else "secondary"):
            st.session_state.sub_remate_opcion = "En Vivo"
            st.rerun()
    with col_sub2:
        if st.button("ADELANTADOS", key="btn_sub_adelantados", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Adelantados" else "secondary"):
            st.session_state.sub_remate_opcion = "Adelantados"
            st.rerun()
    with col_sub3:
        if st.button("CIEGOS", key="btn_sub_ciegos", use_container_width=True, type="primary" if st.session_state.sub_remate_opcion == "Ciegos" else "secondary"):
            st.session_state.sub_remate_opcion = "Ciegos"
            st.rerun()

    modo_actual = st.session_state.sub_remate_opcion
    carreras_del_modo = st.session_state.carreras_por_modalidad.get(modo_actual, lista_carreras_disponibles)

    if not carreras_del_modo:
        st.info("No hay carreras configuradas para esta modalidad.")
    else:
        carrera_sel = st.selectbox("Seleccionar Carrera", carreras_del_modo, key="select_carrera_remate")
        
        detalles = st.session_state.detalles_carreras.get(carrera_sel, {"condicion": "-", "distancia": "-", "hora": "-", "incentivo": 0.0})
        
        # Tarjeta informativa de la carrera
        st.markdown(f"""
            <div class="carrera-condicion-card">
                <b>📋 {carrera_sel}</b> | 📐 Distancia: <b>{detalles.get('distancia')}</b> | ⏰ Hora: <b>{detalles.get('hora')}</b><br>
                <i>{detalles.get('condicion')}</i>
            </div>
        """, unsafe_allow_html=True)
        
        if detalles.get("incentivo", 0.0) > 0:
            st.markdown(f"""
                <div class="incentivo-elegante">
                    <div class="incentivo-elegante-titulo">🎁 Incentivo Especial de la Casa</div>
                    <div class="incentivo-elegante-monto">{formatear_bs(detalles['incentivo'])}</div>
                </div>
            """, unsafe_allow_html=True)

        esta_cerrada = st.session_state.carreras_cerradas_remate.get(carrera_sel, False)
        
        if esta_cerrada:
            st.markdown("<div class='timer-box'>🔴 REMATE CERRADO PARA ESTA CARRERA</div>", unsafe_allow_html=True)
        
        # Muestra la tabla de postores y montos actuales
        dict_remates_carrera = st.session_state.remates.get(carrera_sel, {})
        tabla_html = generar_tabla_html_remate(dict_remates_carrera)
        st.markdown(tabla_html, unsafe_allow_html=True)

        # Panel de Puja para usuarios si la carrera está abierta
        if not esta_cerrada:
            st.markdown("<div class='subasta-header'>⚡ REALIZAR PUJA EN VIVO</div>", unsafe_allow_html=True)
            
            ejemplares_lista = list(dict_remates_carrera.keys())
            if ejemplares_lista:
                col_p1, col_p2 = st.columns([1, 1])
                
                with col_p1:
                    ejemplar_a_pujar = st.selectbox("Ejemplar", ejemplares_lista, key="sel_ejemplar_puja")
                    monto_actual_ej = dict_remates_carrera[ejemplar_a_pujar]["monto"]
                    opciones_monto = obtener_siguientes_montos(monto_actual_ej)
                    monto_seleccionado = st.selectbox("Monto a Pujar (Bs.)", opciones_monto, key="sel_monto_puja")

                with col_p2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔥 CONFIRMAR PUJA", use_container_width=True, type="primary"):
                        usuario = st.session_state.usuario_activo
                        
                        # Actualización de la puja
                        st.session_state.remates[carrera_sel][ejemplar_a_pujar] = {
                            "jugador": usuario,
                            "monto": float(monto_seleccionado)
                        }
                        
                        # Registro en la cuenta del usuario
                        if usuario not in st.session_state.cuentas:
                            st.session_state.cuentas[usuario] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                        
                        # Recalcular el total acumulado de pujas del usuario
                        total_pujas_user = 0.0
                        for c_k, c_v in st.session_state.remates.items():
                            for ej_k, ej_v in c_v.items():
                                if ej_v["jugador"] == usuario:
                                    total_pujas_user += ej_v["monto"]
                        
                        st.session_state.cuentas[usuario]['Pujas'] = total_pujas_user
                        st.success(f"¡Puja registrada! {usuario} ofreció {formatear_bs(monto_seleccionado)} por {ejemplar_a_pujar}")
                        st.rerun()

# ------------------------------------------------------------------------------
# OPCIÓN 2: DUPLETAS / POLLAS HÍPICAS
# ------------------------------------------------------------------------------
elif st.session_state.menu_principal_opcion == "Dupletas":
    col_d1, col_d2, col_d3 = st.columns(3, gap="small")
    with col_d1:
        if st.button("DUPLETA", key="btn_sub_dupleta", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Dupleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Dupleta"
            st.rerun()
    with col_d2:
        if st.button("TRIPLETA", key="btn_sub_tripleta", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Tripleta" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Tripleta"
            st.rerun()
    with col_d3:
        if st.button("POLLA HÍPICA", key="btn_sub_polla", use_container_width=True, type="primary" if st.session_state.sub_dupleta_opcion == "Polla Hipica" else "secondary"):
            st.session_state.sub_dupleta_opcion = "Polla Hipica"
            st.rerun()

    sub_modalidad = st.session_state.sub_dupleta_opcion
    st.subheader(f"🎟️ Jugada Especial: {sub_modalidad}")
    
    monto_fijo = st.session_state.config_montos_especiales.get(sub_modalidad, 500.0)
    st.info(f"Monto por combinación: **{formatear_bs(monto_fijo)}**")

    if st.session_state.dupleta_bloqueada:
        st.error("🔒 Las jugadas especiales se encuentran temporalmente cerradas por la administración.")
    else:
        if sub_modalidad == "Dupleta":
            carreras_disponibles_spec = st.session_state.carreras_habilitadas_dupleta
            num_carreras_req = 2
        elif sub_modalidad == "Tripleta":
            carreras_disponibles_spec = st.session_state.carreras_habilitadas_tripleta
            num_carreras_req = 3
        else:
            carreras_disponibles_spec = st.session_state.carreras_habilitadas_polla
            num_carreras_req = len(carreras_disponibles_spec)

        if len(carreras_disponibles_spec) < num_carreras_req:
            st.warning(f"Se requieren al menos {num_carreras_req} carreras configuradas para esta modalidad.")
        else:
            carreras_seleccionadas_jugada = carreras_disponibles_spec[:num_carreras_req]
            
            selecciones = {}
            col_selec = st.columns(len(carreras_seleccionadas_jugada))
            
            for idx, c_nombre in enumerate(carreras_seleccionadas_jugada):
                with col_selec[idx]:
                    st.markdown(f"**{c_nombre}**")
                    opciones_cab = st.session_state.banco_caballos_por_carrera.get(c_nombre, [])
                    if opciones_cab:
                        selecciones[c_nombre] = st.selectbox(f"Seleccionar Ejemplar", opciones_cab, key=f"spec_{sub_modalidad}_{c_nombre}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"🎯 Sellar Ticket de {sub_modalidad}", type="primary", use_container_width=True):
                usuario = st.session_state.usuario_activo
                
                ticket = {
                    "usuario": usuario,
                    "modalidad": sub_modalidad,
                    "monto": monto_fijo,
                    "jugadas": selecciones,
                    "fecha": datetime.now().strftime("%d/%m/%Y %I:%M %p")
                }
                
                if sub_modalidad == "Dupleta":
                    st.session_state.dupletas_tickets.append(ticket)
                elif sub_modalidad == "Tripleta":
                    st.session_state.tripleta_tickets.append(ticket)
                else:
                    st.session_state.polla_tickets.append(ticket)

                # Descontar / Sumar a la cuenta
                if usuario not in st.session_state.cuentas:
                    st.session_state.cuentas[usuario] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                
                st.session_state.cuentas[usuario]['Pujas'] += monto_fijo
                st.success(f"¡Ticket de {sub_modalidad} registrado exitosamente para {usuario}!")
                st.rerun()

# ------------------------------------------------------------------------------
# OPCIÓN 3: CUENTAS
# ------------------------------------------------------------------------------
elif st.session_state.menu_principal_opcion == "Cuentas":
    st.subheader("📊 Estado de Cuentas General")

    df_cuentas = []
    for usr, datos in st.session_state.cuentas.items():
        total_pujas = datos['Pujas']
        total_premios = datos['Premios']
        total_abonos = datos['Abonos']
        saldo = total_pujas - total_abonos - total_premios
        
        df_cuentas.append({
            "Usuario": usr,
            "Total Jugado (Bs.)": formatear_bs(total_pujas),
            "Abonos (Bs.)": formatear_bs(total_abonos),
            "Premios (Bs.)": formatear_bs(total_premios),
            "Balance Neto": formatear_bs(saldo),
            "Estado": "Deuda 🔴" if saldo > 0 else ("A Favor 🟢" if saldo < 0 else "Al Día 🔵")
        })

    st.dataframe(pd.DataFrame(df_cuentas), use_container_width=True)

    # Panel de Administración de Usuarios y Pagos
    st.markdown("---")
    st.subheader("💳 Registrar Abonos / Pagos de Clientes")
    
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        usr_abono = st.selectbox("Cliente", list(st.session_state.cuentas.keys()), key="sel_usr_abono")
    with col_a2:
        monto_abono = st.number_input("Monto de Abono (Bs.)", min_value=0.0, step=100.0, key="num_monto_abono")
    with col_a3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Cargar Abono", use_container_width=True):
            if monto_abono > 0:
                st.session_state.cuentas[usr_abono]['Abonos'] += monto_abono
                st.success(f"Se cargó un abono de {formatear_bs(monto_abono)} a {usr_abono}")
                st.rerun()
            else:
                st.error("Ingrese un monto válido mayor a 0.")

    # Opción para agregar nuevos usuarios
    st.markdown("---")
    st.subheader("👤 Crear Nuevo Usuario")
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        nuevo_usuario_nombre = st.text_input("Nombre o Seudónimo del Jugador", key="txt_nuevo_usuario")
    with col_u2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Crear Usuario", use_container_width=True):
            nombre_limpio = nuevo_usuario_nombre.strip().upper()
            if nombre_limpio:
                if nombre_limpio not in st.session_state.lista_usuarios:
                    st.session_state.lista_usuarios.append(nombre_limpio)
                    st.session_state.cuentas[nombre_limpio] = {'Pujas': 0.0, 'Premios': 0.0, 'Abonos': 0.0}
                    st.success(f"Usuario '{nombre_limpio}' registrado con éxito.")
                    st.rerun()
                else:
                    st.warning("El usuario ya existe.")
            else:
                st.error("Ingrese un nombre válido.")
