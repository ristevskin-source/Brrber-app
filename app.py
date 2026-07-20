import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# ---------- CUSTOM CSS (Još svetlija tamna tema) ----------
st.markdown("""
<style>
    /* Glavna pozadina - svetlija */
    .stApp {
        background-color: #3a3a3a;
        color: #ffffff;
    }
    /* Naslovi */
    h1, h2, h3 {
        color: #d4af37 !important;
    }
    /* Kartica za potvrdu */
    .potvrda-kartica {
        background-color: #4a4a4a;
        padding: 20px;
        border-radius: 15px;
        border-left: 6px solid #d4af37;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        margin: 20px 0;
    }
    .potvrda-kartica p {
        color: #ffffff;
    }
    /* Zebra redovi */
    .zebra-red {
        background-color: #4a4a4a;
        padding: 8px 0;
        border-radius: 8px;
        margin: 4px 0;
        color: #ffffff;
    }
    .zebra-red:nth-child(even) {
        background-color: #404040;
    }
    /* Dugmad */
    .stButton button {
        background-color: #d4af37 !important;
        color: #1a1a1a !important;
        font-weight: bold !important;
        border-radius: 20px !important;
        border: none !important;
        transition: 0.3s;
    }
    .stButton button:hover {
        background-color: #e6c86a !important;
        transform: scale(1.02);
    }
    /* Otkaži dugme */
    .otkazi-dugme button {
        background-color: #b22222 !important;
        color: white !important;
    }
    .otkazi-dugme button:hover {
        background-color: #d43b3b !important;
    }
    /* Inputi i select */
    .stSelectbox, .stTextInput, .stNumberInput {
        background-color: #4a4a4a !important;
        color: #ffffff !important;
    }
    .stSelectbox div[role="listbox"] {
        background-color: #4a4a4a !important;
    }
    /* Metrike */
    .stMetric {
        background-color: #4a4a4a;
        border-radius: 12px;
        padding: 10px;
        border: 1px solid #d4af37;
        color: #ffffff;
    }
    .stMetric label, .stMetric div {
        color: #ffffff !important;
    }
    /* Alerti */
    .stAlert {
        background-color: #4a4a4a !important;
        color: #ffffff !important;
    }
    /* Label */
    label {
        color: #f0f0f0 !important;
    }
    /* Tabovi */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #4a4a4a;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #ffffff;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d4af37 !important;
        color: #1a1a1a !important;
        font-weight: bold;
    }
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        background: #3a3a3a;
    }
    ::-webkit-scrollbar-thumb {
        background: #d4af37;
        border-radius: 10px;
    }
    /* Stil za celu sliku (preko ekrana) */
    .full-width-image {
        width: 100%;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ---------- KONFIGURACIJA ----------
RADNO_VREME = [(9,0), (20,0)]
INTERVAL_MIN = 60
BROJ_DANA = 7

# ---------- INICIJALIZACIJA BAZE ----------
def init_db():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije 
                 (id INTEGER PRIMARY KEY, usluga TEXT, datum TEXT, vreme TEXT, 
                  ime TEXT, telefon TEXT, cena INTEGER)''')
    
    c.execute("PRAGMA table_info(rezervacije)")
    kolone = [info[1] for info in c.fetchall()]
    if 'naplaceno' not in kolone:
        c.execute("ALTER TABLE rezervacije ADD COLUMN naplaceno INTEGER DEFAULT 0")
    if 'datum_naplate' not in kolone:
        c.execute("ALTER TABLE rezervacije ADD COLUMN datum_naplate TEXT")
    
    c.execute("UPDATE rezervacije SET datum_naplate = datum WHERE naplaceno=1 AND datum_naplate IS NULL")
    
    c.execute('''CREATE TABLE IF NOT EXISTS cenovnik (usluga TEXT PRIMARY KEY, cena INTEGER)''')
    default_cene = [('Šišanje', 2000), ('Brijanje', 700), ('Stilizovanje', 1000)]
    c.executemany("INSERT OR IGNORE INTO cenovnik VALUES (?, ?)", default_cene)
    
    c.execute('''CREATE TABLE IF NOT EXISTS konfiguracija (lozinka TEXT)''')
    c.execute("SELECT * FROM konfiguracija")
    if not c.fetchone():
        c.execute("INSERT INTO konfiguracija (lozinka) VALUES ('1234')")
    
    c.execute('''CREATE TABLE IF NOT EXISTS pauze 
                 (id INTEGER PRIMARY KEY, datum TEXT, vreme TEXT, napomena TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ---------- POMOĆNE FUNKCIJE ----------
def formatiraj_datum(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    dani_u_nedelji = ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak", "Subota", "Nedelja"]
    return f"{dani_u_nedelji[dan.weekday()]}, {dan.strftime('%d.%m.%Y')}"

def generisi_datume():
    now = datetime.now()
    if now.hour >= 20:
        start = now + timedelta(days=1)
    else:
        start = now
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    datumi = []
    for i in range(BROJ_DANA):
        dan = start + timedelta(days=i)
        datumi.append(dan.strftime("%Y-%m-%d"))
    return datumi

def generisi_termine_za_dan(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    if dan.weekday() == 6:
        return
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute("SELECT vreme FROM pauze WHERE datum=?", (datum_str,))
    pauze = [row[0] for row in c.fetchall()]
    
    c.execute("DELETE FROM rezervacije WHERE datum=? AND ime IS NULL", (datum_str,))
    
    sat_start, min_start = RADNO_VREME[0]
    sat_kraj, min_kraj = RADNO_VREME[1]
    trenutno = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_start, minute=min_start)
    kraj = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_kraj, minute=min_kraj)
    
    termini = []
    while trenutno < kraj:
        vreme = trenutno.strftime("%H:%M")
        if vreme not in pauze:
            termini.append((None, datum_str, vreme, None, None, None))
        trenutno += timedelta(minutes=INTERVAL_MIN)
    
    if termini:
        c.executemany("INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena) VALUES (?, ?, ?, ?, ?, ?)", termini)
        conn.commit()
    conn.close()

def osvezi_termine():
    datumi = generisi_datume()
    for d in datumi:
        generisi_termine_za_dan(d)

osvezi_termine()

# ---------- UI ----------
# 🔥 SLIKA - PREKO CELOG EKRANA (širina 100%)
try:
    st.image("IMG-7dca0f9a0a28a9b8098a0cf36f04adb2-V.jpg", use_container_width=True)
except:
    pass

st.title("💈 Berberski salon - Zakazivanje")

# ---------- TABOVI ----------
tab1, tab2 = st.tabs(["📅 Zakazivanje", "🔑 Admin Panel"])

# ===================================================================
# TAB 1: KLIJENTI
# ===================================================================
with tab1:
    if 'booking_success' not in st.session_state:
        st.session_state['booking_success'] = False

    if st.session_state['booking_success']:
        detalji = st.session_state['booking_details']
        st.balloons()
        st.markdown(f"""
        <div class="potvrda-kartica">
            <h2 style="color: #d4af37; margin:0;">✅ Uspešno ste zakazali!</h2>
            <p><strong>Usluga:</strong> {detalji['usluga']}</p>
            <p><strong>Datum:</strong> {formatiraj_datum(detalji['datum'])}</p>
            <p><strong>Vreme:</strong> {detalji['vreme']}</p>
            <p><strong>Cena:</strong> {detalji['cena']} din</p>
            <p><strong>Klijent:</strong> {detalji['ime']}</p>
            <p style="margin-top:15px; font-size:1.2em; color:#d4af37;">✂️ Vidimo se!</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📅 Zakaži novi termin"):
            st.session_state['booking_success'] = False
            st.rerun()
    else:
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        datumi_raw = generisi_datume()
        c.execute("SELECT usluga, cena FROM cenovnik")
        cenovnik_dict = dict(c.fetchall())
        conn.close()
        
        if datumi_raw and cenovnik_dict:
            with st.form("klijent_forma"):
                ime = st.text_input("Ime i prezime *")
                tel = st.text_input("Telefon *")
                usluga = st.selectbox("Usluga", list(cenovnik_dict.keys()))
                datum = st.selectbox("Datum", datumi_raw, format_func=formatiraj_datum)
                
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("SELECT id, vreme FROM rezervacije WHERE datum=? AND ime IS NULL", (datum,))
                slobodni = c.fetchall()
                conn.close()
                
                if slobodni:
                    mapa = {t[1]: t[0] for t in slobodni}
                    termin = st.selectbox("Slobodan termin", list(mapa.keys()))
                    
                    if st.form_submit_button("Zakaži"):
                        cena = cenovnik_dict[usluga]
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("UPDATE rezervacije SET ime=?, telefon=?, usluga=?, cena=? WHERE id=?", 
                                  (ime, tel, usluga, cena, mapa[termin]))
                        conn.commit()
                        conn.close()
                        
                        st.session_state['booking_success'] = True
                        st.session_state['booking_details'] = {
                            'usluga': usluga,
                            'datum': datum,
                            'vreme': termin,
                            'cena': cena,
                            'ime': ime
                        }
                        st.rerun()
                else:
                    st.warning("⏳ Nema slobodnih termina za izabrani datum.")
        else:
            st.error("❌ Baza je prazna.")

# ===================================================================
# TAB 2: ADMIN
# ===================================================================
with tab2:
    if "admin" not in st.session_state:
        st.session_state.admin = False
    
    if not st.session_state.admin:
        lozinka = st.text_input("Lozinka:", type="password")
        if lozinka == "1234":
            st.session_state.admin = True
            st.rerun()
    else:
        # ---------- STATISTIKA ----------
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        
        c.execute("SELECT count(*) FROM rezervacije WHERE datum=? AND ime IS NOT NULL", (today,))
        danas_klijenata = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM rezervacije WHERE ime IS NOT NULL AND (naplaceno IS NULL OR naplaceno=0)")
        nenaplaceno = c.fetchone()[0]
        
        conn.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📅 Danas", f"{danas_klijenata} klijenata")
        with col2:
            st.metric("⏳ Čeka naplatu", f"{nenaplaceno}")
        
        # ---------- FINANSIJSKI IZVEŠTAJ ----------
        st.subheader("📊 Finansijski izveštaj")
        
        this_month = datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate=?", (today,))
        danas_promet = c.fetchone()[0] or 0
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE ?", (f"{this_month}%",))
        mesec_promet = c.fetchone()[0] or 0
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1")
        ukupno_promet = c.fetchone()[0] or 0
        
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📅 Danas", f"{danas_promet} din")
        with col2:
            st.metric("📆 Ovaj mesec", f"{mesec_promet} din")
        with col3:
            st.metric("💰 Ukupno", f"{ukupno_promet} din")
        
        # ---------- PREGLED PROMETA PO MESECIMA ----------
        st.subheader("📈 Promet po mesecima")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT substr(datum_naplate,1,7) FROM rezervacije WHERE naplaceno=1 AND datum_naplate IS NOT NULL ORDER BY datum_naplate DESC")
        dostupni_meseci = [row[0] for row in c.fetchall()]
        conn.close()
        
        if dostupni_meseci:
            izabrani_mesec = st.selectbox("Izaberite mesec", dostupni_meseci, index=0)
            
            conn = sqlite3.connect('termini.db')
            c = conn.cursor()
            c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE ?", (f"{izabrani_mesec}%",))
            promet_mesec = c.fetchone()[0] or 0
            conn.close()
            
            st.write(f"### Promet za {izabrani_mesec}: **{promet_mesec} din**")
        else:
            st.info("📭 Još uvek nema naplaćenih usluga.")
        
        # ---------- TABELA ZAKAZANIH KLIJENATA ----------
        st.subheader("📋 Zakazani klijenti")
        
        pretraga = st.text_input("🔍 Pretraži po imenu", placeholder="Unesi ime...")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        if pretraga:
            c.execute("""
                SELECT id, ime, usluga, datum, vreme, cena, naplaceno 
                FROM rezervacije 
                WHERE ime IS NOT NULL AND ime LIKE ? 
                ORDER BY datum ASC, vreme ASC
            """, (f"%{pretraga}%",))
        else:
            c.execute("""
                SELECT id, ime, usluga, datum, vreme, cena, naplaceno 
                FROM rezervacije 
                WHERE ime IS NOT NULL 
                ORDER BY datum ASC, vreme ASC
            """)
        svi_klijenti = c.fetchall()
        conn.close()
        
        if svi_klijenti:
            st.markdown("---")
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([0.3, 1.5, 1.3, 1.2, 1.0, 1.0, 1.0, 0.8])
            with col1: st.write("**#**")
            with col2: st.write("**Ime**")
            with col3: st.write("**Usluga**")
            with col4: st.write("**Datum**")
            with col5: st.write("**Vreme**")
            with col6: st.write("**Cena**")
            with col7: st.write("**Status**")
            with col8: st.write("**Akcija**")
            st.markdown("---")
            
            for idx, red in enumerate(svi_klijenti, start=1):
                id, ime, usluga, datum, vreme, cena, naplaceno = red
                
                bg_color = "#4a4a4a" if idx % 2 == 0 else "#404040"
                
                st.markdown(f'<div style="background-color:{bg_color}; border-radius:8px; padding:6px 0; margin:2px 0;">', unsafe_allow_html=True)
                
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([0.3, 1.5, 1.3, 1.2, 1.0, 1.0, 1.0, 0.8])
                with col1:
                    st.write(f"{idx}.")
                with col2:
                    st.write(ime)
                with col3:
                    st.write(usluga)
                with col4:
                    st.write(formatiraj_datum(datum))
                with col5:
                    st.write(vreme)
                with col6:
                    st.write(f"{cena} din")
                with col7:
                    if naplaceno == 1:
                        st.write("✅ Naplaćeno")
                    else:
                        if f"paid_{id}" not in st.session_state:
                            st.session_state[f"paid_{id}"] = False
                        if st.session_state[f"paid_{id}"]:
                            st.write("⏳ Naplaćivanje...")
                        else:
                            if st.button(f"💰 Naplati", key=f"pay_{id}"):
                                conn = sqlite3.connect('termini.db')
                                c = conn.cursor()
                                c.execute("UPDATE rezervacije SET naplaceno=1, datum_naplate=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d"), id))
                                conn.commit()
                                conn.close()
                                st.session_state[f"paid_{id}"] = True
                                st.success(f"✅ Naplaćeno: {ime}")
                                st.rerun()
                with col8:
                    if naplaceno == 0 or naplaceno is None:
                        st.markdown('<div class="otkazi-dugme">', unsafe_allow_html=True)
                        if st.button(f"🗑️ Otkaži", key=f"cancel_{id}"):
                            conn = sqlite3.connect('termini.db')
                            c = conn.cursor()
                            c.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, naplaceno=0 WHERE id=?", (id,))
                            conn.commit()
                            conn.close()
                            st.success(f"🗑️ Otkazano: {ime}")
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.write("🔒")
                
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")
        else:
            st.info("📭 Trenutno nema zakazanih klijenata.")
        
        # ---------- UPRAVLJANJE USLUGAMA ----------
        st.subheader("📝 Upravljanje uslugama")
        with st.form("dodaj_uslugu"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                nova_usluga = st.text_input("Naziv nove usluge")
            with col2:
                nova_cena = st.number_input("Cena (din)", min_value=0, step=100)
            with col3:
                if st.form_submit_button("➕ Dodaj"):
                    if nova_usluga and nova_cena > 0:
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("INSERT OR IGNORE INTO cenovnik VALUES (?, ?)", (nova_usluga, nova_cena))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Dodato: {nova_usluga} - {nova_cena} din")
                        st.rerun()
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT usluga, cena FROM cenovnik")
        sve_usluge = c.fetchall()
        conn.close()
        
        for usluga, cena in sve_usluge:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{usluga}**")
            with col2:
                st.write(f"{cena} din")
            with col3:
                nova_cena = st.number_input(f"Nova cena", value=cena, step=100, key=f"cena_{usluga}")
                if st.button(f"💾 Sačuvaj", key=f"save_{usluga}"):
                    conn = sqlite3.connect('termini.db')
                    c = conn.cursor()
                    c.execute("UPDATE cenovnik SET cena=? WHERE usluga=?", (nova_cena, usluga))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Cena za {usluga} ažurirana!")
                    st.rerun()
        
        # ---------- UPRAVLJANJE PAUZAMA ----------
        st.subheader("⏸️ Pauze (blokirani termini)")
        with st.form("dodaj_pauzu"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                datum_pauze = st.selectbox("Datum", generisi_datume(), format_func=formatiraj_datum)
            with col2:
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("SELECT vreme FROM rezervacije WHERE datum=? AND ime IS NULL", (datum_pauze,))
                slobodna_vremena = [r[0] for r in c.fetchall()]
                conn.close()
                if slobodna_vremena:
                    vreme_pauze = st.selectbox("Vreme", slobodna_vremena)
                else:
                    vreme_pauze = st.text_input("Vreme (HH:MM)")
            with col3:
                napomena = st.text_input("Napomena")
            if st.form_submit_button("➕ Dodaj pauzu"):
                if datum_pauze and vreme_pauze:
                    conn = sqlite3.connect('termini.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO pauze (datum, vreme, napomena) VALUES (?, ?, ?)", 
                              (datum_pauze, vreme_pauze, napomena or "Pauza"))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Pauza dodata za {datum_pauze} u {vreme_pauze}")
                    st.rerun()
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT id, datum, vreme, napomena FROM pauze ORDER BY datum, vreme")
        sve_pauze = c.fetchall()
        conn.close()
        
        if sve_pauze:
            for id, datum, vreme, napomena in sve_pauze:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{formatiraj_datum(datum)}** {vreme}")
                with col2:
                    st.write(napomena if napomena else "Pauza")
                with col3:
                    if st.button(f"🗑️ Obriši", key=f"del_pauza_{id}"):
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM pauze WHERE id=?", (id,))
                        conn.commit()
                        conn.close()
                        st.success("🗑️ Pauza obrisana!")
                        st.rerun()
        else:
            st.info("📭 Trenutno nema zakazanih pauza.")
