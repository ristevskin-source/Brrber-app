import streamlit as st
import sqlite3
import os
from datetime import datetime, timedelta

# ---------- BRISANJE STARE BAZE ----------
if os.path.exists("termini.db"):
    os.remove("termini.db")
    st.info("🗑️ Stara baza je obrisana. Kreiram novu...")

# ---------- CUSTOM CSS ----------
st.markdown("""
<style>
    .stApp { background-color: #3a3a3a; color: #ffffff; }
    h1, h2, h3 { color: #d4af37 !important; }
    .potvrda-kartica {
        background-color: #4a4a4a;
        padding: 20px;
        border-radius: 15px;
        border-left: 6px solid #d4af37;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        margin: 20px 0;
    }
    .potvrda-kartica p { color: #ffffff; }
    .stAlert[data-baseweb="notification"] {
        background-color: #1a3a5c !important;
        color: #d4af37 !important;
        border-left: 4px solid #d4af37 !important;
    }
    .stAlert[data-baseweb="notification"] .stMarkdown { color: #d4af37 !important; }
    .stAlert[data-baseweb="notification"] .stMarkdown p { color: #d4af37 !important; }
    .stAlert[data-baseweb="notification"]:has(.stAlertIcon[data-icon="warning"]) {
        background-color: #5c4a1a !important;
        color: #fff0d0 !important;
        border-left: 4px solid #d4af37 !important;
    }
    .stAlert[data-baseweb="notification"]:has(.stAlertIcon[data-icon="error"]) {
        background-color: #5c1a1a !important;
        color: #ffd0d0 !important;
        border-left: 4px solid #c24a4a !important;
    }
    .stAlert[data-baseweb="notification"]:has(.stAlertIcon[data-icon="success"]) {
        background-color: #1a4a2a !important;
        color: #d0ffd0 !important;
        border-left: 4px solid #4ac24a !important;
    }
    .klijent-kartica {
        background-color: #4a4a4a;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
        border: 2px solid #d4af37;
        box-shadow: 0 2px 8px rgba(212, 175, 55, 0.15);
        transition: 0.2s;
    }
    .klijent-kartica:hover {
        box-shadow: 0 4px 16px rgba(212, 175, 55, 0.3);
        transform: scale(1.002);
    }
    .klijent-kartica .redni-broj { color: #d4af37; font-weight: bold; font-size: 1.1em; }
    .klijent-kartica .ime-klijenta { color: #ffffff; font-weight: bold; font-size: 1.1em; }
    .klijent-kartica .detalji { color: #d0d0d0; font-size: 0.95em; }
    .klijent-kartica .cena { color: #d4af37; font-weight: bold; }
    .stButton button {
        background-color: #d4af37 !important;
        color: #1a1a1a !important;
        font-weight: bold !important;
        border-radius: 20px !important;
        border: none !important;
        transition: 0.3s;
    }
    .stButton button:hover { background-color: #e6c86a !important; transform: scale(1.02); }
    .otkazi-dugme button { background-color: #b22222 !important; color: white !important; }
    .otkazi-dugme button:hover { background-color: #d43b3b !important; }
    .stSelectbox, .stTextInput, .stNumberInput { background-color: #4a4a4a !important; color: #ffffff !important; }
    .stSelectbox div[role="listbox"] { background-color: #4a4a4a !important; }
    .stMetric { background-color: #4a4a4a; border-radius: 12px; padding: 10px; border: 1px solid #d4af37; color: #ffffff; }
    .stMetric label, .stMetric div { color: #ffffff !important; }
    label { color: #f0f0f0 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #4a4a4a;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #ffffff;
    }
    .stTabs [aria-selected="true"] { background-color: #d4af37 !important; color: #1a1a1a !important; font-weight: bold; }
    ::-webkit-scrollbar { width: 8px; background: #3a3a3a; }
    ::-webkit-scrollbar-thumb { background: #d4af37; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------- KONFIGURACIJA ----------
RADNO_VREME = [(9,0), (20,0)]
INTERVAL_MIN = 15
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS cenovnik (
                    usluga TEXT PRIMARY KEY, 
                    cena INTEGER,
                    trajanje INTEGER
                )''')
    
    usluge = [
        ('💇 Šišanje', 1500, 45),
        ('💇 Šišanje + pranje kose', 1900, 60),
        ('💇 Šišanje + brada', 2000, 60),
        ('💇 Šišanje + brada + pranje kose', 2400, 75),
        ('💇 Šišanje + brada + pranje kose + obrve', 2800, 90),
        ('🧔 Brada (samo)', 1000, 30),
        ('✨ Obrve (samo)', 400, 15)
    ]
    c.executemany("INSERT OR IGNORE INTO cenovnik (usluga, cena, trajanje) VALUES (?, ?, ?)", usluge)
    
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

def generisi_slotove_za_dan(datum_str):
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
    
    slotovi = []
    while trenutno < kraj:
        vreme = trenutno.strftime("%H:%M")
        if vreme not in pauze:
            slotovi.append((None, datum_str, vreme, None, None, None))
        trenutno += timedelta(minutes=INTERVAL_MIN)
    
    if slotovi:
        c.executemany("INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena) VALUES (?, ?, ?, ?, ?, ?)", slotovi)
        conn.commit()
    conn.close()

def osvezi_termine():
    datumi = generisi_datume()
    for d in datumi:
        generisi_slotove_za_dan(d)

osvezi_termine()

def dovoljno_slobodnih_slotova(datum, pocetak, trajanje):
    broj_slotova = trajanje // INTERVAL_MIN
    if trajanje % INTERVAL_MIN != 0:
        broj_slotova += 1
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("""
        SELECT vreme FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND ime IS NULL 
        ORDER BY vreme ASC
    """, (datum, pocetak))
    slobodni = [row[0] for row in c.fetchall()]
    conn.close()
    
    if len(slobodni) < broj_slotova:
        return False
    
    for i in range(broj_slotova - 1):
        t1 = datetime.strptime(slobodni[i], "%H:%M")
        t2 = datetime.strptime(slobodni[i+1], "%H:%M")
        if (t2 - t1).seconds // 60 != INTERVAL_MIN:
            return False
    return True

def rezervisi_slotove(datum, pocetak, trajanje, ime, telefon, usluga, cena):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    broj_slotova = trajanje // INTERVAL_MIN
    if trajanje % INTERVAL_MIN != 0:
        broj_slotova += 1
    
    c.execute("""
        SELECT id FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND ime IS NULL 
        ORDER BY vreme ASC LIMIT ?
    """, (datum, pocetak, broj_slotova))
    ids = [row[0] for row in c.fetchall()]
    
    for id in ids:
        c.execute("""
            UPDATE rezervacije 
            SET ime=?, telefon=?, usluga=?, cena=? 
            WHERE id=?
        """, (ime, telefon, usluga, cena, id))
    
    conn.commit()
    conn.close()

# ---------- UI ----------
try:
    st.image("IMG-7dca0f9a0a28a9b8098a0cf36f04adb2-V.jpg", use_column_width=True)
except:
    pass

st.title("💈 Berberski salon - Zakazivanje")

tab1, tab2 = st.tabs(["📅 Zakazivanje", "🔑 Admin Panel"])

# ===================================================================
# TAB 1: KLIJENTI
# ===================================================================
with tab1:
    # 🔍 DEBUG
    with st.expander("🔍 Debug info (klikni da vidiš)"):
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        
        c.execute("SELECT * FROM cenovnik")
        usluge_iz_baze = c.fetchall()
        st.write("📋 Usluge u bazi:", usluge_iz_baze)
        
        c.execute("SELECT COUNT(*) FROM rezervacije")
        broj_slotova = c.fetchone()[0]
        st.write("📅 Broj slotova u bazi:", broj_slotova)
        
        # 🔥 Provera zakazanih klijenata
        c.execute("SELECT COUNT(*) FROM rezervacije WHERE ime IS NOT NULL")
        broj_klijenata = c.fetchone()[0]
        st.write("👤 Broj zakazanih klijenata:", broj_klijenata)
        
        if broj_klijenata > 0:
            c.execute("SELECT ime, usluga, datum, vreme FROM rezervacije WHERE ime IS NOT NULL")
            klijenti = c.fetchall()
            st.write("📋 Klijenti:", klijenti)
        
        if st.button("🔄 Ručno generiši slotove (rešava problem)"):
            osvezi_termine()
            st.success("✅ Slotovi su regenerisani! Osvežite stranicu.")
            st.rerun()
        
        conn.close()
    
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
            <p><strong>Trajanje:</strong> {detalji['trajanje']} min</p>
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
        c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
        usluge = c.fetchall()
        conn.close()
        
        st.info(f"🔍 Pronađeno {len(usluge)} usluga i {len(datumi_raw)} datuma.")
        
        if datumi_raw and usluge:
            with st.form("klijent_forma"):
                ime = st.text_input("Ime i prezime *")
                tel = st.text_input("Telefon *")
                
                usluga_opcije = [f"{u[0]} ({u[2]} min, {u[1]} din)" for u in usluge]
                izabrana = st.selectbox("Usluga", usluga_opcije)
                
                idx = usluga_opcije.index(izabrana)
                usluga_ime = usluge[idx][0]
                usluga_cena = usluge[idx][1]
                usluga_trajanje = usluge[idx][2]
                
                datum = st.selectbox("Datum", datumi_raw, format_func=formatiraj_datum)
                
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("SELECT vreme FROM rezervacije WHERE datum=? AND ime IS NULL ORDER BY vreme ASC", (datum,))
                svi_slotovi = [row[0] for row in c.fetchall()]
                conn.close()
                
                slobodni_termini = []
                for slot in svi_slotovi:
                    if dovoljno_slobodnih_slotova(datum, slot, usluga_trajanje):
                        slobodni_termini.append(slot)
                
                if slobodni_termini:
                    termin = st.selectbox("Slobodan termin", slobodni_termini)
                    
                    if st.form_submit_button("Zakaži"):
                        rezervisi_slotove(datum, termin, usluga_trajanje, ime, tel, usluga_ime, usluga_cena)
                        
                        st.session_state['booking_success'] = True
                        st.session_state['booking_details'] = {
                            'usluga': usluga_ime,
                            'datum': datum,
                            'vreme': termin,
                            'trajanje': usluga_trajanje,
                            'cena': usluga_cena,
                            'ime': ime
                        }
                        st.rerun()
                else:
                    st.warning("⏳ Nema dovoljno slobodnih termina za ovu uslugu na izabrani datum.")
        else:
            st.error("❌ Baza je prazna. Kliknite na 'Ručno generiši slotove' u debug delu.")

# ===================================================================
# TAB 2: ADMIN
# ===================================================================
with tab2:
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("UPDATE konfiguracija SET lozinka='1234'")
    conn.commit()
    conn.close()
    
    if "admin" not in st.session_state:
        st.session_state.admin = False
    
    if not st.session_state.admin:
        lozinka = st.text_input("Lozinka:", type="password")
        if lozinka == "1234":
            st.session_state.admin = True
            st.rerun()
    else:
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
        
        st.subheader("📋 Zakazani klijenti")
        
        pretraga = st.text_input("🔍 Pretraži po imenu", placeholder="Unesi ime...")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        if pretraga:
            c.execute("""
                SELECT id, ime, telefon, usluga, datum, vreme, cena, naplaceno 
                FROM rezervacije 
                WHERE ime IS NOT NULL AND ime LIKE ? 
                ORDER BY datum ASC, vreme ASC
            """, (f"%{pretraga}%",))
        else:
            c.execute("""
                SELECT id, ime, telefon, usluga, datum, vreme, cena, naplaceno 
                FROM rezervacije 
                WHERE ime IS NOT NULL 
                ORDER BY datum ASC, vreme ASC
            """)
        svi_klijenti = c.fetchall()
        conn.close()
        
        if svi_klijenti:
            st.markdown("---")
            col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([0.3, 1.3, 1.0, 1.2, 1.2, 0.8, 0.9, 0.9, 0.8])
            with col1: st.markdown("**#**")
            with col2: st.markdown("**Ime**")
            with col3: st.markdown("**📞 Telefon**")
            with col4: st.markdown("**Usluga**")
            with col5: st.markdown("**Datum**")
            with col6: st.markdown("**Vreme**")
            with col7: st.markdown("**Cena**")
            with col8: st.markdown("**Status**")
            with col9: st.markdown("**Akcija**")
            st.markdown("---")
            
            for idx, red in enumerate(svi_klijenti, start=1):
                id, ime, telefon, usluga, datum, vreme, cena, naplaceno = red
                
                st.markdown(f"""
                <div class="klijent-kartica">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                            <span class="redni-broj">#{idx}</span>
                            <span class="ime-klijenta">{ime}</span>
                            <span class="detalji">📞 {telefon if telefon else 'Nije unet'}</span>
                            <span class="detalji">✂️ {usluga}</span>
                            <span class="detalji">📅 {formatiraj_datum(datum)}</span>
                            <span class="detalji">⏰ {vreme}</span>
                            <span class="cena">{cena} din</span>
                        </span>
                        <span style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                """, unsafe_allow_html=True)
                
                if naplaceno == 1:
                    st.markdown('<span style="color: #4ac24a; font-weight: bold;">✅ Naplaćeno</span>', unsafe_allow_html=True)
                    st.markdown('<span style="color: #666;">🔒</span>', unsafe_allow_html=True)
                else:
                    if f"paid_{id}" not in st.session_state:
                        st.session_state[f"paid_{id}"] = False
                    
                    if st.session_state[f"paid_{id}"]:
                        st.markdown('<span style="color: #d4af37;">⏳ Naplaćivanje...</span>', unsafe_allow_html=True)
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
                    
                    st.markdown('<div class="otkazi-dugme" style="display: inline-block;">', unsafe_allow_html=True)
                    if st.button(f"🗑️ Otkaži", key=f"cancel_{id}"):
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, naplaceno=0 WHERE id=?", (id,))
                        conn.commit()
                        conn.close()
                        st.success(f"🗑️ Otkazano: {ime}")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown("""
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("---")
        else:
            st.info("📭 Trenutno nema zakazanih klijenata.")
        
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
                        c.execute("INSERT OR IGNORE INTO cenovnik (usluga, cena, trajanje) VALUES (?, ?, ?)", (nova_usluga, nova_cena, 60))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Dodato: {nova_usluga} - {nova_cena} din (podrazumevano 60 min)")
                        st.rerun()
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT usluga, cena, trajanje FROM cenovnik")
        sve_usluge = c.fetchall()
        conn.close()
        
        for usluga, cena, trajanje in sve_usluge:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.write(f"**{usluga}**")
            with col2:
                st.write(f"{cena} din")
            with col3:
                novo_trajanje = st.number_input(f"Trajanje (min)", value=trajanje, step=15, key=f"trajanje_{usluga}")
            with col4:
                nova_cena = st.number_input(f"Nova cena", value=cena, step=100, key=f"cena_{usluga}")
                if st.button(f"💾 Sačuvaj", key=f"save_{usluga}"):
                    conn = sqlite3.connect('termini.db')
                    c = conn.cursor()
                    c.execute("UPDATE cenovnik SET cena=?, trajanje=? WHERE usluga=?", (nova_cena, novo_trajanje, usluga))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Usluga {usluga} ažurirana!")
                    st.rerun()
        
        st.subheader("⏸️ Pauze (blokirani termini)")
        with st.form("dodaj_pauzu"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                datum_pauze = st.selectbox("Datum", generisi_datume(), format_func=formatiraj_datum)
            with col2:
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("SELECT vreme FROM rezervacije WHERE datum=? AND ime IS NULL", (datum_pauze,))
                slobodna_vremena = [row[0] for row in c.fetchall()]
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
